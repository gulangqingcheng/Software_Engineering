"""
面试题接口路由
提供 AI 面试题生成、题库查询等功能
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.question import InterviewQuestion, QuestionCategory, QuestionDifficulty, QuestionSource
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse

router = APIRouter(prefix="/api/v1/question", tags=["面试题"])


class QuestionGenerateRequest(BaseModel):
    """面试题生成请求"""
    role: str | None = Field(default=None, description="目标岗位/方向")
    category: str = Field(default="general", description="题目分类")
    difficulty: str = Field(default="medium", description="难度：easy / medium / hard")
    count: int = Field(default=5, ge=1, le=20, description="生成题目数量")
    topic: str | None = Field(default=None, description="具体知识点（可选，如 Vue3、链表）")
    resume_id: int | None = Field(default=None, description="简历ID（可选，用于个性化出题）")
    resume_text: str | None = Field(default=None, description="简历文本（可选，用于个性化出题）")


class QuestionItem(BaseModel):
    """单个面试题"""
    id: int | None = None
    user_id: int | None = None
    question: str
    category: str
    difficulty: str
    reference_answer: str | None = None
    tags: list[str] | None = None
    type: str | None = None
    source: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class QuestionCreateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    category: str = "general"
    difficulty: str = "medium"
    reference_answer: str | None = None
    tags: list[str] | None = None


class QuestionUpdateRequest(BaseModel):
    question: str | None = None
    category: str | None = None
    difficulty: str | None = None
    reference_answer: str | None = None
    tags: list[str] | None = None


class DuplicateQuestionGroup(BaseModel):
    question: str
    items: list[QuestionItem]


class DuplicateResolveRequest(BaseModel):
    keep_id: int = Field(..., description="要保留的题目 ID")
    remove_ids: list[int] | None = Field(default=None, description="要删除的重复题目 ID；为空则删除同题目的其他记录")


def _to_question_item(question: InterviewQuestion) -> QuestionItem:
    return QuestionItem(
        id=question.id,
        user_id=question.user_id,
        question=question.question,
        category=question.category.value if hasattr(question.category, "value") else str(question.category),
        difficulty=question.difficulty.value if hasattr(question.difficulty, "value") else str(question.difficulty),
        reference_answer=question.reference_answer,
        tags=question.tags if isinstance(question.tags, list) else [],
        source=question.source.value if hasattr(question.source, "value") else str(question.source),
        created_at=question.created_at,
    )


def _different_answer_duplicate_groups(questions: list[InterviewQuestion]) -> list[DuplicateQuestionGroup]:
    grouped: dict[str, list[InterviewQuestion]] = {}
    for item in questions:
        key = (item.question or "").strip()
        if not key:
            continue
        grouped.setdefault(key, []).append(item)

    groups: list[DuplicateQuestionGroup] = []
    for question_text, items in grouped.items():
        answers = {(item.reference_answer or "").strip() for item in items}
        if len(items) > 1 and len(answers) > 1:
            groups.append(DuplicateQuestionGroup(
                question=question_text,
                items=[_to_question_item(item) for item in items],
            ))
    return groups


def _dedupe_exact_questions(db: Session, user_id: int) -> None:
    """Delete exact duplicate personal records with the same question and answer."""
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.user_id == user_id
    ).order_by(InterviewQuestion.created_at.asc(), InterviewQuestion.id.asc()).all()
    seen: set[tuple[str, str]] = set()
    changed = False
    for item in questions:
        key = ((item.question or "").strip(), (item.reference_answer or "").strip())
        if key in seen:
            db.delete(item)
            changed = True
        else:
            seen.add(key)
    if changed:
        db.commit()


@router.post(
    "/generate",
    response_model=APIResponse[list[QuestionItem]],
    summary="AI 生成面试题",
)
async def generate_questions(
    request: QuestionGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """使用 Tavily 搜索 + RAG + DeepSeek 生成面试题"""

    # 验证参数
    valid_categories = [c.value for c in QuestionCategory]
    if request.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的分类。可选: {', '.join(valid_categories)}",
        )

    valid_difficulties = [d.value for d in QuestionDifficulty]
    if request.difficulty not in valid_difficulties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的难度。可选: {', '.join(valid_difficulties)}",
        )

    resume_text = request.resume_text
    if request.resume_id and not resume_text:
        from app.models.resume import Resume

        resume = db.query(Resume).filter(
            Resume.id == request.resume_id,
            Resume.user_id == current_user.id,
        ).first()
        if resume and resume.parsed_content:
            resume_text = str(resume.parsed_content)

    topic = request.topic or request.role

    # 调用 QuestionAgent 生成题目
    from app.agents.question_agent import QuestionAgent
    agent = QuestionAgent()
    questions = await agent.generate(
        category=request.category,
        difficulty=request.difficulty,
        count=request.count,
        topic=topic,
        resume_text=resume_text,
    )

    # 保存到数据库
    saved_ids = await agent.save_to_db(
        questions=questions,
        category=request.category,
        difficulty=request.difficulty,
        user_id=current_user.id,
    )

    # 同时存入 ChromaDB RAG（供后续检索用）
    try:
        from app.services.rag_service import RAGService
        rag = RAGService()
        await rag.add_documents(
            documents=[q.get("question", "") for q in questions],
            metadatas=[{"category": request.category, "difficulty": request.difficulty} for _ in questions],
        )
    except Exception:
        pass  # RAG 存储失败不影响主流程

    # 构建返回结果
    result_items = []
    for q_data, q_id in zip(questions, saved_ids):
        result_items.append(QuestionItem(
            id=q_id,
            user_id=current_user.id,
            question=q_data.get("question", ""),
            category=request.category,
            difficulty=request.difficulty,
            reference_answer=q_data.get("reference_answer"),
            tags=q_data.get("tags", [request.category, request.difficulty]),
            type=q_data.get("type"),
            source=QuestionSource.AI_GENERATED.value,
        ))

    return APIResponse(
        data=result_items,
        message=f"成功生成 {len(result_items)} 道面试题",
    )


@router.get(
    "/library",
    response_model=APIResponse[PaginatedResponse[QuestionItem]],
    summary="获取题库列表",
)
async def list_questions(
    category: str | None = Query(default=None, description="按分类筛选"),
    difficulty: str | None = Query(default=None, description="按难度筛选"),
    keyword: str | None = Query(default=None, description="按关键词搜索"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    mine: bool = Query(default=False, description="仅查看我的个性化题库"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取面试题库列表，支持筛选和分页"""

    query = db.query(InterviewQuestion)
    if mine:
        _dedupe_exact_questions(db, current_user.id)
        query = query.filter(InterviewQuestion.user_id == current_user.id)

    if category:
        query = query.filter(InterviewQuestion.category == category)
    if difficulty:
        query = query.filter(InterviewQuestion.difficulty == difficulty)
    if keyword:
        query = query.filter(InterviewQuestion.question.contains(keyword))

    total = query.count()
    questions = (
        query
        .order_by(InterviewQuestion.usage_count.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return APIResponse(
        data=PaginatedResponse(
        data=[_to_question_item(q) for q in questions],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/duplicates",
    response_model=APIResponse[list[DuplicateQuestionGroup]],
    summary="获取我的重复题目",
)
async def list_duplicate_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回题目完全相同但答案不同的个人题库记录。"""
    _dedupe_exact_questions(db, current_user.id)
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.user_id == current_user.id
    ).all()
    return APIResponse(data=_different_answer_duplicate_groups(questions))


@router.post(
    "/duplicates/resolve",
    response_model=APIResponse[None],
    summary="处理重复题目",
)
async def resolve_duplicate_questions(
    request: DuplicateResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保留一条重复题目记录，删除同题目的其他个人记录。"""
    keep = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == request.keep_id,
        InterviewQuestion.user_id == current_user.id,
    ).first()
    if not keep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="要保留的题目不存在")

    query = db.query(InterviewQuestion).filter(
        InterviewQuestion.user_id == current_user.id,
        InterviewQuestion.question == keep.question,
        InterviewQuestion.id != keep.id,
    )
    if request.remove_ids is not None:
        query = query.filter(InterviewQuestion.id.in_(request.remove_ids))

    deleted = 0
    for item in query.all():
        db.delete(item)
        deleted += 1
    db.commit()
    return APIResponse(data=None, message=f"已删除 {deleted} 条重复题目")


@router.get(
    "/library/{question_id}",
    response_model=APIResponse[QuestionItem],
    summary="获取单个面试题",
)
async def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定面试题的详细信息（含参考答案）"""
    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == question_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="面试题不存在",
        )
    if question.user_id and question.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该题目")

    # 更新使用次数
    question.usage_count += 1
    db.commit()

    return APIResponse(data=_to_question_item(question))


@router.post(
    "/create",
    response_model=APIResponse[QuestionItem],
    summary="创建面试题",
)
async def create_question(
    request: QuestionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建一条人工维护的题库题目"""
    try:
        category = QuestionCategory(request.category)
    except ValueError:
        category = QuestionCategory.GENERAL
    try:
        difficulty = QuestionDifficulty(request.difficulty)
    except ValueError:
        difficulty = QuestionDifficulty.MEDIUM

    question = InterviewQuestion(
        user_id=current_user.id,
        question=request.question,
        category=category,
        difficulty=difficulty,
        reference_answer=request.reference_answer,
        tags=request.tags or [category.value, difficulty.value],
        source=QuestionSource.USER_UPLOADED,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return APIResponse(data=_to_question_item(question), message="创建成功")


@router.put(
    "/library/{question_id}",
    response_model=APIResponse[QuestionItem],
    summary="更新面试题",
)
async def update_question(
    question_id: int,
    request: QuestionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新题库题目"""
    question = db.query(InterviewQuestion).filter(InterviewQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试题不存在")
    if question.user_id and question.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该题目")

    if request.question is not None:
        question.question = request.question
    if request.category is not None:
        try:
            question.category = QuestionCategory(request.category)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效分类")
    if request.difficulty is not None:
        try:
            question.difficulty = QuestionDifficulty(request.difficulty)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效难度")
    if request.reference_answer is not None:
        question.reference_answer = request.reference_answer
    if request.tags is not None:
        question.tags = request.tags

    db.commit()
    db.refresh(question)
    return APIResponse(data=_to_question_item(question), message="更新成功")


@router.delete(
    "/library/{question_id}",
    response_model=APIResponse[None],
    summary="删除面试题",
)
async def delete_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除题库题目"""
    question = db.query(InterviewQuestion).filter(InterviewQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试题不存在")
    if question.user_id and question.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除该题目")

    db.delete(question)
    db.commit()
    return APIResponse(data=None, message="删除成功")
