"""
简历接口路由
提供简历上传、解析、评估、查重等功能
"""

import os
import uuid
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.resume import Resume, ResumeStatus
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.resume import (
    ResumeEvaluationResponse,
    ResumeListResponse,
    ResumeResponse,
)

router = APIRouter(prefix="/api/v1/resume", tags=["简历"])
logger = logging.getLogger(__name__)

# 扩展支持的文件类型：增加图片格式
ALLOWED_RESUME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
]


def _get_upload_subdir() -> str:
    """获取按日期组织的上传子目录路径"""
    from datetime import date
    today = date.today()
    subdir = os.path.join(
        settings.UPLOAD_DIR, "resumes", str(today.year), f"{today.month:02d}"
    )
    os.makedirs(subdir, exist_ok=True)
    return subdir


def _extract_text_from_file(file_path: str) -> str:
    """从简历文件中提取纯文本（PDF/DOCX/图片）"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()
        except ImportError:
            logger.warning("[简历] PyMuPDF 未安装，无法提取 PDF 文本")
            return ""
        except Exception as e:
            logger.warning(f"[简历] PDF 文本提取失败: {e}")
            return ""

    elif ext in (".docx", ".doc"):
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs).strip()
        except Exception as e:
            logger.warning(f"[简历] DOCX 文本提取失败: {e}")
            return ""

    # 图片格式无法提取文本，返回空
    return ""


async def _process_resume(resume_id: int):
    """后台任务：评估简历（AI评估 + 查重检测 + 违禁词检测）"""
    from app.database import SessionLocal
    from app.models.resume import Resume, ResumeStatus
    from app.agents.resume_agent import ResumeAgent
    from app.services.plagiarism import PlagiarismChecker
    from app.services.violation import ViolationChecker

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return

        # 更新状态为处理中
        resume.status = ResumeStatus.EVALUATING
        db.commit()

        # 并行执行：AI评估 + 查重 + 违禁词检测
        agent = ResumeAgent()
        # 提取简历文本（用于查重和违禁词检测）。图片简历用 Qwen-VL OCR。
        text = await agent._extract_text(resume.file_path)
        resume.parsed_content = text if text else None

        plagiarism_checker = PlagiarismChecker()
        violation_checker = ViolationChecker()

        async def run_evaluate():
            return await agent.evaluate(resume.file_path)

        async def run_plagiarism():
            if not text:
                return {"score": 0.0, "similar_sources": [], "is_suspicious": False}
            return await plagiarism_checker.check(text)

        async def run_violation():
            if not text:
                return {"words": [], "count": 0, "has_violation": False, "details": []}
            return await violation_checker.check_with_llm(text)

        # 三任务并行执行，单个失败不影响其他
        eval_task = asyncio.create_task(run_evaluate())
        plag_task = asyncio.create_task(run_plagiarism())
        viol_task = asyncio.create_task(run_violation())

        evaluation = {"overall_score": 0, "detailed_analysis": "评估失败"}
        plagiarism_result = {"score": 0.0, "similar_sources": [], "is_suspicious": False}
        violation_result = {"words": [], "count": 0, "has_violation": False, "details": []}

        try:
            evaluation = await eval_task
        except Exception as e:
            logger.error(f"[简历] AI评估失败: {e}", exc_info=True)
            evaluation = {"overall_score": 0, "detailed_analysis": f"AI评估失败: {str(e)}"}

        try:
            plagiarism_result = await plag_task
        except Exception as e:
            logger.error(f"[简历] 查重检测失败: {e}", exc_info=True)

        try:
            violation_result = await viol_task
        except Exception as e:
            logger.error(f"[简历] 违禁词检测失败: {e}", exc_info=True)

        # 保存所有结果到数据库
        resume.evaluation_result = evaluation
        resume.plagiarism_score = plagiarism_result.get("score", 0)
        resume.violation_words = violation_result if violation_result.get("has_violation") else None

        # 将查重和违禁词摘要追加到评估结果中（前端可直接展示）
        evaluation["plagiarism"] = plagiarism_result
        evaluation["violation"] = violation_result

        resume.status = ResumeStatus.COMPLETED
        db.commit()

        logger.info(
            f"[简历] 评估完成 id={resume_id}, "
            f"score={evaluation.get('overall_score', 0)}, "
            f"plagiarism={plagiarism_result.get('score', 0)}, "
            f"violations={violation_result.get('count', 0)}"
        )

    except Exception as e:
        # 更新状态为失败
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.status = ResumeStatus.FAILED
            resume.evaluation_result = {"error": str(e)}
            db.commit()
        logger.error(f"[简历] 处理失败 id={resume_id}: {e}", exc_info=True)
    finally:
        db.close()


@router.post(
    "/upload",
    response_model=APIResponse[ResumeResponse],
    summary="上传简历文件",
)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="简历文件（支持 PDF、Word、JPG、PNG）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传简历文件，自动触发 AI 评估流程"""

    # 验证文件类型
    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}。支持: PDF、Word、JPG、PNG、WebP",
        )

    # 保存文件
    upload_dir = _get_upload_subdir()
    file_ext = os.path.splitext(file.filename or "resume.pdf")[1]
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
    resume = Resume(
        user_id=current_user.id,
        file_path=file_path,
        file_name=file.filename or "resume",
        status=ResumeStatus.UPLOADED,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # 后台异步执行评估
    background_tasks.add_task(_process_resume, resume.id)

    return APIResponse(
        data=ResumeResponse.model_validate(resume),
        message="简历上传成功，正在 AI 评估中...",
    )


class ResumeEvaluateRequest(BaseModel):
    """简历评估请求（指定目标岗位）"""
    target_position: str | None = Field(default=None, description="目标岗位（可选）")


@router.post(
    "/{resume_id}/evaluate",
    response_model=APIResponse[ResumeEvaluationResponse],
    summary="重新评估简历",
)
async def evaluate_resume(
    resume_id: int,
    request: ResumeEvaluateRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对已上传的简历重新进行 AI 评估（可指定目标岗位）"""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在",
        )

    if not os.path.exists(resume.file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="简历文件丢失，请重新上传",
        )

    # 重置状态并触发重新评估
    resume.status = ResumeStatus.UPLOADED
    if request and request.target_position:
        resume.evaluation_result = resume.evaluation_result or {}
        resume.evaluation_result["target_position"] = request.target_position
    db.commit()

    background_tasks.add_task(_process_resume, resume.id)

    return APIResponse(message="已提交重新评估，请稍后查看结果")


@router.get(
    "/list",
    response_model=APIResponse[ResumeListResponse],
    summary="获取简历列表",
)
async def list_resumes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的简历列表"""
    total = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .count()
    )

    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return APIResponse(
        data=ResumeListResponse(
            resumes=[ResumeResponse.model_validate(r) for r in resumes],
            total=total,
        ),
    )


@router.get(
    "/{resume_id}",
    response_model=APIResponse[ResumeResponse],
    summary="获取简历详情",
)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定简历的详细信息"""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在",
        )

    return APIResponse(data=ResumeResponse.model_validate(resume))


@router.get(
    "/{resume_id}/evaluation",
    response_model=APIResponse[ResumeEvaluationResponse],
    summary="获取简历评估结果",
)
async def get_evaluation(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定简历的 AI 评估结果"""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在",
        )

    if resume.status in (ResumeStatus.PARSING, ResumeStatus.EVALUATING):
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="简历正在评估中，请稍后重试",
        )

    if resume.status == ResumeStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="简历评估失败，请重新上传或重试",
        )

    if resume.status != ResumeStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"简历尚未评估完成，当前状态: {resume.status.value}",
        )

    eval_data = resume.evaluation_result or {}

    return APIResponse(
        data=ResumeEvaluationResponse(
            resume_id=resume.id,
            overall_score=eval_data.get("overall_score", 0),
            strengths=eval_data.get("strengths", []),
            weaknesses=eval_data.get("weaknesses", []),
            suggestions=eval_data.get("suggestions", []),
            plagiarism_score=resume.plagiarism_score,
            violation_words=resume.violation_words.get("words", []) if resume.violation_words else None,
            detailed_analysis=eval_data.get("detailed_analysis"),
        ),
    )


@router.delete(
    "/{resume_id}",
    response_model=APIResponse,
    summary="删除简历",
)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除指定简历及其文件"""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在",
        )

    # 删除物理文件
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    db.delete(resume)
    db.commit()

    return APIResponse(message="简历已删除")
