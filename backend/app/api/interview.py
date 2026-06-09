"""AI 面试接口路由。

调用 InterviewAgent 和 InterviewScoringService 处理面试逻辑。
"""

from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.interview_agent import InterviewAgent
from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.interview import InterviewSession, InterviewTurn
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewReportResponse,
    InterviewSessionCreateRequest,
    InterviewSessionDetailResponse,
    InterviewSessionResponse,
)
from app.services.interview_scoring_service import InterviewScoringService

router = APIRouter(prefix="/api/v1/interview", tags=["AI面试"])

# 初始化 agent 和 service
interview_agent = InterviewAgent()
scoring_service = InterviewScoringService()


def _get_session(db: Session, session_id: int, user_id: int) -> InterviewSession:
    """获取面试会话"""
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    return session


def _create_turn(db: Session, session: InterviewSession, question_index: int) -> InterviewTurn:
    """创建面试题目"""
    question_info = interview_agent.generate_question(
        target_position=session.target_position,
        interview_type=session.interview_type,
        difficulty=session.difficulty,
        question_index=question_index,
    )
    turn = InterviewTurn(
        session_id=session.id,
        question_index=question_index,
        question=question_info["question"],
    )
    db.add(turn)
    db.flush()
    return turn


def _save_report(db: Session, session: InterviewSession) -> InterviewReportResponse:
    """生成并保存面试报告"""
    report = scoring_service.generate_report(session)
    session.total_score = report["total_score"]
    session.report = {**report, "generated_at": report["generated_at"].isoformat()}
    db.commit()
    db.refresh(session)
    return InterviewReportResponse.model_validate(report)


def _write_docx_report(session: InterviewSession, report: dict) -> BytesIO:
    """生成 Word 格式面试报告"""
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Pt

    document = Document()
    for style_name in ["Normal", "Title", "Heading 1", "Heading 2", "Heading 3"]:
        style = document.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(12 if style_name == "Normal" else 14)

    document.add_heading(f"{session.title} - 面试评估报告", level=0)
    document.add_paragraph(f"目标岗位：{session.target_position}")
    document.add_paragraph(f"面试类型：{session.interview_type}    难度：{session.difficulty}")
    document.add_paragraph(f"综合评分：{report.get('total_score', 0)}/100")
    document.add_paragraph(f"生成时间：{report.get('generated_at')}")

    document.add_heading("一、评分依据", level=1)
    document.add_paragraph(report.get("score_basis") or "")

    document.add_heading("二、总体评价", level=1)
    document.add_paragraph(report.get("summary") or "")

    document.add_heading("三、维度得分", level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "评分维度"
    hdr[1].text = "得分"
    hdr[2].text = "满分"
    for name, score in (report.get("dimension_scores") or {}).items():
        row = table.add_row().cells
        row[0].text = str(name)
        row[1].text = str(score)
        row[2].text = str(scoring_service.DIMENSIONS.get(name, ""))

    document.add_heading("四、逐题分析", level=1)
    for turn in report.get("turn_performance") or []:
        document.add_heading(f"第 {turn.get('question_index')} 题：{turn.get('score')}/100", level=2)
        document.add_paragraph(f"题目：{turn.get('question')}")
        document.add_paragraph(f"回答：{turn.get('answer') or '未记录'}")
        duration = turn.get("answer_duration_seconds")
        document.add_paragraph(f"回答时长：{duration if duration is not None else '未记录'} 秒")
        document.add_paragraph(f"评价：{turn.get('feedback')}")
        document.add_paragraph("评分依据：")
        for item in turn.get("evidence") or []:
            document.add_paragraph(str(item), style="List Bullet")
        document.add_paragraph("扣分点：")
        for item in turn.get("missing_points") or []:
            document.add_paragraph(str(item), style="List Bullet")
        document.add_paragraph(f"改进建议：{turn.get('suggestion')}")

    document.add_heading("五、优势与不足", level=1)
    document.add_paragraph("优势：")
    for item in report.get("strengths") or []:
        document.add_paragraph(str(item), style="List Bullet")
    document.add_paragraph("不足：")
    for item in report.get("weaknesses") or []:
        document.add_paragraph(str(item), style="List Bullet")

    document.add_heading("六、改进建议与训练计划", level=1)
    for item in report.get("suggestions") or []:
        document.add_paragraph(str(item), style="List Bullet")
    document.add_paragraph("训练计划：")
    for item in report.get("action_plan") or []:
        document.add_paragraph(str(item), style="List Number")

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output


@router.post("/sessions", response_model=APIResponse[InterviewSessionResponse], summary="创建面试会话")
async def create_session(
    request: InterviewSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = InterviewSession(
        user_id=current_user.id,
        title=request.title or f"{request.target_position} AI面试",
        target_position=request.target_position,
        interview_type=request.interview_type,
        difficulty=request.difficulty,
        question_count=request.question_count,
        answer_mode=request.answer_mode,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return APIResponse(data=InterviewSessionResponse.model_validate(session), message="面试会话创建成功")


@router.get("/sessions", response_model=APIResponse[PaginatedResponse[InterviewSessionResponse]], summary="获取面试会话列表")
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(InterviewSession).filter(InterviewSession.user_id == current_user.id)
    total = query.count()
    sessions = (
        query.order_by(InterviewSession.created_at.desc(), InterviewSession.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return APIResponse(
        data=PaginatedResponse(
            data=[InterviewSessionResponse.model_validate(item) for item in sessions],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/sessions/{session_id}", response_model=APIResponse[InterviewSessionDetailResponse], summary="获取面试会话详情")
async def get_session_detail(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    return APIResponse(data=InterviewSessionDetailResponse.model_validate(session))


@router.post("/sessions/{session_id}/start", response_model=APIResponse[InterviewSessionDetailResponse], summary="开始面试")
async def start_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    if session.status == "finished":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="面试已结束")

    if session.status == "pending":
        session.status = "in_progress"
        session.started_at = datetime.now()

    if not session.turns:
        _create_turn(db, session, 1)

    db.commit()
    db.refresh(session)
    return APIResponse(data=InterviewSessionDetailResponse.model_validate(session), message="面试已开始")


@router.post("/sessions/{session_id}/answer", response_model=APIResponse[InterviewSessionDetailResponse], summary="提交当前问题回答")
async def answer_session(
    session_id: int,
    request: InterviewAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    if session.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="面试尚未开始或已经结束")

    turn = next((item for item in session.turns if item.answered_at is None), None)
    if not turn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前没有待回答的问题")

    result = scoring_service.score(
        session=session,
        turn=turn,
        answer_text=request.answer_text or "",
        answer_duration_seconds=request.answer_duration_seconds,
    )
    turn.answer_text = request.answer_text.strip() if request.answer_text else None
    turn.answer_audio_url = request.answer_audio_url
    turn.answer_duration_seconds = request.answer_duration_seconds
    turn.answered_at = datetime.now()
    turn.score = result["score"]
    turn.feedback = result["feedback"]
    turn.suggestion = result["suggestion"]

    if turn.question_index < session.question_count:
        _create_turn(db, session, turn.question_index + 1)

    db.commit()
    db.refresh(session)
    return APIResponse(data=InterviewSessionDetailResponse.model_validate(session), message="回答提交成功")


@router.post("/sessions/{session_id}/finish", response_model=APIResponse[InterviewReportResponse], summary="结束面试")
async def finish_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    if session.status == "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="面试尚未开始")

    if session.status != "finished":
        session.status = "finished"
        session.ended_at = datetime.now()

    report = _save_report(db, session)
    return APIResponse(data=report, message="面试已结束")


@router.get("/sessions/{session_id}/report", response_model=APIResponse[InterviewReportResponse], summary="获取面试报告")
async def get_session_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    if not session.report:
        report = _save_report(db, session)
    else:
        report = InterviewReportResponse.model_validate(session.report)
    return APIResponse(data=report)


@router.get("/sessions/{session_id}/report.docx", summary="下载 Word 面试报告")
async def download_session_report_docx(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    if not session.report:
        report = _save_report(db, session).model_dump()
    else:
        report = session.report
    output = _write_docx_report(session, report)
    filename = quote(f"{session.title}-面试报告.docx")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
