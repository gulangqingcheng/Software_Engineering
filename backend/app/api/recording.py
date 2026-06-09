"""
录音接口路由
提供面试录音上传、ASR 转写、分析结果查询等功能
"""

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.recording import InterviewRecording, RecordingStatus
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.recording import (
    RecordingAnalysisResponse,
    RecordingListResponse,
    RecordingResponse,
)

router = APIRouter(prefix="/api/v1/recording", tags=["录音"])


def _get_upload_subdir() -> str:
    """获取按日期组织的上传子目录路径"""
    from datetime import date
    today = date.today()
    subdir = os.path.join(
        settings.UPLOAD_DIR, "recordings", str(today.year), f"{today.month:02d}"
    )
    os.makedirs(subdir, exist_ok=True)
    return subdir


async def _process_recording(recording_id: int):
    """后台任务：ASR 转写 + AI 分析"""
    from app.database import SessionLocal
    from app.models.recording import InterviewRecording, RecordingStatus
    from app.agents.recording_agent import RecordingAgent

    db = SessionLocal()
    try:
        recording = db.query(InterviewRecording).filter(
            InterviewRecording.id == recording_id
        ).first()
        if not recording:
            return

        # 更新状态为处理中
        recording.status = RecordingStatus.ANALYZING
        db.commit()

        # 调用 Agent 处理
        agent = RecordingAgent()
        result = await agent.process(recording.file_path, user_id=recording.user_id)

        # 保存结果
        recording.transcript = result["transcript"]
        recording.duration_seconds = result["duration_seconds"]
        recording.analysis_result = result["analysis"]
        recording.collected_questions = {
            "questions": result["analysis"].get("collected_questions", [])
        }
        recording.status = RecordingStatus.COMPLETED
        db.commit()

    except Exception as e:
        recording = db.query(InterviewRecording).filter(
            InterviewRecording.id == recording_id
        ).first()
        if recording:
            recording.status = RecordingStatus.FAILED
            recording.analysis_result = {"error": str(e)}
            db.commit()
    finally:
        db.close()


@router.post(
    "/upload",
    response_model=APIResponse[RecordingResponse],
    summary="上传面试录音",
)
async def upload_recording(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="音频文件（支持 wav、mp3、m4a、webm）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传面试录音文件，触发异步 ASR 转写和分析流程"""

    # 验证文件类型
    if file.content_type not in settings.ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的音频格式: {file.content_type}。支持: wav, mp3, m4a, webm",
        )

    # 保存文件
    upload_dir = _get_upload_subdir()
    file_ext = os.path.splitext(file.filename or "recording.wav")[1]
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, unique_name)

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    recording = InterviewRecording(
        user_id=current_user.id,
        file_path=file_path,
        file_name=file.filename or "recording",
        status=RecordingStatus.UPLOADED,
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)

    # 后台异步执行转写和分析
    background_tasks.add_task(_process_recording, recording.id)

    return APIResponse(
        data=RecordingResponse.model_validate(recording),
        message="录音上传成功，正在 ASR 转写和 AI 分析中...",
    )


@router.get(
    "/list",
    response_model=APIResponse[RecordingListResponse],
    summary="获取录音列表",
)
async def list_recordings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的录音列表"""
    total = (
        db.query(InterviewRecording)
        .filter(InterviewRecording.user_id == current_user.id)
        .count()
    )

    recordings = (
        db.query(InterviewRecording)
        .filter(InterviewRecording.user_id == current_user.id)
        .order_by(InterviewRecording.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return APIResponse(
        data=RecordingListResponse(
            recordings=[RecordingResponse.model_validate(r) for r in recordings],
            total=total,
        ),
    )


@router.get(
    "/{recording_id}",
    response_model=APIResponse[RecordingResponse],
    summary="获取录音详情",
)
async def get_recording(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定录音的详细信息"""
    recording = (
        db.query(InterviewRecording)
        .filter(
            InterviewRecording.id == recording_id,
            InterviewRecording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="录音不存在",
        )

    return APIResponse(data=RecordingResponse.model_validate(recording))


@router.get(
    "/{recording_id}/status",
    response_model=APIResponse[dict],
    summary="查询录音处理状态",
)
async def get_recording_status(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询录音的 ASR 转写和分析处理进度"""
    recording = (
        db.query(InterviewRecording)
        .filter(
            InterviewRecording.id == recording_id,
            InterviewRecording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="录音不存在",
        )

    return APIResponse(
        data={
            "id": recording.id,
            "status": recording.status.value,
            "file_name": recording.file_name,
        },
    )


@router.get(
    "/{recording_id}/analysis",
    response_model=APIResponse[RecordingAnalysisResponse],
    summary="获取录音分析结果",
)
async def get_analysis(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取录音的 ASR 转写文本和 AI 分析结果"""
    recording = (
        db.query(InterviewRecording)
        .filter(
            InterviewRecording.id == recording_id,
            InterviewRecording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="录音不存在",
        )

    if recording.status in (RecordingStatus.TRANSCRIBING, RecordingStatus.ANALYZING):
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="录音正在处理中，请稍后重试",
        )

    if recording.status == RecordingStatus.FAILED:
        error_msg = "处理失败，请重试"
        if recording.analysis_result and recording.analysis_result.get("error"):
            error_msg = f"处理失败: {recording.analysis_result['error']}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )

    if recording.status != RecordingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"录音分析尚未完成，当前状态: {recording.status.value}",
        )

    analysis = recording.analysis_result or {}

    return APIResponse(
        data=RecordingAnalysisResponse(
            recording_id=recording.id,
            transcript=recording.transcript,
            duration_seconds=recording.duration_seconds or 0,
            fluency_score=analysis.get("fluency_score"),
            speech_rate=analysis.get("speech_rate"),
            key_points=analysis.get("key_points", []),
            suggestions=analysis.get("suggestions", []),
            collected_questions=recording.collected_questions,
        ),
    )


@router.delete(
    "/{recording_id}",
    response_model=APIResponse,
    summary="删除录音",
)
async def delete_recording(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除指定录音及其文件"""
    recording = (
        db.query(InterviewRecording)
        .filter(
            InterviewRecording.id == recording_id,
            InterviewRecording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="录音不存在",
        )

    # 删除物理文件
    if os.path.exists(recording.file_path):
        os.remove(recording.file_path)

    db.delete(recording)
    db.commit()

    return APIResponse(message="录音已删除")
