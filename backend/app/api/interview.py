"""
AI 面试接口路由
使用确定性问题模板和基础评分，保证本地无需外部 LLM 也可运行。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
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

router = APIRouter(prefix="/api/v1/interview", tags=["AI面试"])

QUESTION_TEMPLATES = {
    "technical": [
        "请介绍你在{position}方向最有代表性的项目，以及你承担的核心职责。",
        "在{position}工作中遇到复杂问题时，你通常如何定位原因并验证解决方案？",
        "请结合实例说明你如何保证交付质量，并处理性能、稳定性或可维护性问题。",
        "如果需要你从零设计一个与{position}相关的功能，你会如何拆解需求和制定方案？",
        "请谈谈你近期学习的一项与{position}相关的新技术，以及它适合解决什么问题。",
    ],
    "behavioral": [
        "请介绍一次你主动推动团队目标达成的经历。",
        "请描述一次你与团队成员意见不一致的情况，以及你如何处理。",
        "请分享一次你面对紧迫期限时安排优先级的经历。",
        "请说明一次失败或失误给你带来的经验。",
        "你为什么希望从事{position}相关工作，未来的成长目标是什么？",
    ],
    "comprehensive": [
        "请做一个简短的自我介绍，并说明你与{position}岗位的匹配点。",
        "请介绍一个最能体现你解决问题能力的项目经历。",
        "面对不熟悉的任务时，你会如何快速学习并交付结果？",
        "请描述你如何与团队协作并保证信息同步。",
        "你对{position}岗位的核心能力有哪些理解？",
    ],
}


def _get_session(db: Session, session_id: int, user_id: int) -> InterviewSession:
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    return session


def _generate_question(session: InterviewSession, question_index: int) -> str:
    templates = QUESTION_TEMPLATES.get(
        session.interview_type,
        QUESTION_TEMPLATES["comprehensive"],
    )
    template = templates[(question_index - 1) % len(templates)]
    difficulty_label = {"easy": "基础", "medium": "进阶", "hard": "深入"}.get(
        session.difficulty,
        "进阶",
    )
    return f"第 {question_index} 题（{difficulty_label}）：{template.format(position=session.target_position)}"


def _create_turn(db: Session, session: InterviewSession, question_index: int) -> InterviewTurn:
    turn = InterviewTurn(
        session_id=session.id,
        question_index=question_index,
        question=_generate_question(session, question_index),
    )
    db.add(turn)
    db.flush()
    return turn


def _score_answer(request: InterviewAnswerRequest) -> tuple[float, str, str]:
    answer = (request.answer_text or "").strip()
    if answer:
        length = len(answer)
        if length < 20:
            score = 50.0
        elif length < 60:
            score = 65.0
        elif length < 150:
            score = 78.0
        else:
            score = 86.0

        structure_markers = ("首先", "其次", "最后", "例如", "因此", "结果", "第一", "第二")
        score += min(sum(marker in answer for marker in structure_markers) * 2, 8)
    else:
        score = 65.0

    duration = request.answer_duration_seconds
    if duration is not None:
        if 30 <= duration <= 180:
            score += 4
        elif duration < 10:
            score -= 5

    score = round(max(0.0, min(score, 100.0)), 2)
    if score >= 85:
        feedback = "回答内容充分，结构清晰，并体现了较好的岗位理解。"
        suggestion = "继续补充可量化结果，让优势更有说服力。"
    elif score >= 70:
        feedback = "回答覆盖了主要信息，具备一定条理性。"
        suggestion = "建议使用具体案例，并说明你的行动和最终结果。"
    else:
        feedback = "回答较为简略，关键信息和论证还不够完整。"
        suggestion = "建议按背景、任务、行动、结果的结构组织回答。"
    return score, feedback, suggestion


def _build_report(session: InterviewSession) -> dict:
    answered_turns = [turn for turn in session.turns if turn.answered_at is not None]
    scores = [float(turn.score or 0) for turn in answered_turns]
    total_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    if total_score >= 85:
        summary = "整体表现优秀，回答完整且具有较强的岗位匹配度。"
    elif total_score >= 70:
        summary = "整体表现良好，基础能力较扎实，部分回答仍可进一步具体化。"
    else:
        summary = "整体表现仍有提升空间，建议加强回答结构和案例细节。"

    suggestions = list(dict.fromkeys(
        turn.suggestion for turn in answered_turns if turn.suggestion
    ))
    if not suggestions:
        suggestions = ["建议完成更多题目，并使用具体案例展示能力。"]

    return {
        "session_id": session.id,
        "total_score": total_score,
        "status": session.status,
        "summary": summary,
        "turn_performance": [
            {
                "question_index": turn.question_index,
                "question": turn.question,
                "score": float(turn.score or 0),
                "feedback": turn.feedback or "",
                "suggestion": turn.suggestion or "",
            }
            for turn in answered_turns
        ],
        "suggestions": suggestions,
        "generated_at": datetime.now(),
    }


def _save_report(db: Session, session: InterviewSession) -> InterviewReportResponse:
    report = _build_report(session)
    session.total_score = report["total_score"]
    session.report = {
        **report,
        "generated_at": report["generated_at"].isoformat(),
    }
    db.commit()
    db.refresh(session)
    return InterviewReportResponse.model_validate(report)


@router.post(
    "/sessions",
    response_model=APIResponse[InterviewSessionResponse],
    summary="创建面试会话",
)
async def create_session(
    request: InterviewSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = InterviewSession(
        user_id=current_user.id,
        title=request.title or f"{request.target_position} AI 面试",
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


@router.get(
    "/sessions",
    response_model=APIResponse[PaginatedResponse[InterviewSessionResponse]],
    summary="获取面试会话列表",
)
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


@router.get(
    "/sessions/{session_id}",
    response_model=APIResponse[InterviewSessionDetailResponse],
    summary="获取面试会话详情",
)
async def get_session_detail(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    return APIResponse(data=InterviewSessionDetailResponse.model_validate(session))


@router.post(
    "/sessions/{session_id}/start",
    response_model=APIResponse[InterviewSessionDetailResponse],
    summary="开始面试",
)
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


@router.post(
    "/sessions/{session_id}/answer",
    response_model=APIResponse[InterviewSessionDetailResponse],
    summary="提交当前问题回答",
)
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

    score, feedback, suggestion = _score_answer(request)
    turn.answer_text = request.answer_text.strip() if request.answer_text else None
    turn.answer_audio_url = request.answer_audio_url
    turn.answer_duration_seconds = request.answer_duration_seconds
    turn.answered_at = datetime.now()
    turn.score = score
    turn.feedback = feedback
    turn.suggestion = suggestion

    if turn.question_index < session.question_count:
        _create_turn(db, session, turn.question_index + 1)

    db.commit()
    db.refresh(session)
    return APIResponse(data=InterviewSessionDetailResponse.model_validate(session), message="回答提交成功")


@router.post(
    "/sessions/{session_id}/finish",
    response_model=APIResponse[InterviewReportResponse],
    summary="结束面试",
)
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


@router.get(
    "/sessions/{session_id}/report",
    response_model=APIResponse[InterviewReportResponse],
    summary="获取面试报告",
)
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
