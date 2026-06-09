"""
后台管理接口路由
提供仪表盘数据、用户管理、Agent 监控等管理功能
仅限 admin 角色访问
"""

from datetime import datetime, timedelta
from pathlib import Path
import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.agent_log import AgentLog
from app.models.conversation import Conversation
from app.models.question import InterviewQuestion
from app.models.recording import InterviewRecording
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.common import APIResponse

router = APIRouter(prefix="/api/v1/admin", tags=["后台管理"])


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """验证当前用户是否为管理员"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_users: int = Field(description="用户总数")
    total_conversations: int = Field(description="对话总数")
    total_resumes: int = Field(description="简历总数")
    total_recordings: int = Field(description="录音总数")
    total_questions: int = Field(description="题库题目数")
    active_users_today: int = Field(description="今日活跃用户数")
    total_agent_calls: int = Field(description="Agent调用总次数")
    avg_latency_ms: float | None = Field(default=None, description="平均响应延迟")


@router.get(
    "/dashboard",
    response_model=APIResponse[DashboardStats],
    summary="获取仪表盘数据",
)
async def get_dashboard(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取后台管理仪表盘的统计数据"""
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())

    # 统计各项数据
    total_users = db.query(User).count()
    total_conversations = db.query(Conversation).count()
    total_resumes = db.query(Resume).count()
    total_recordings = db.query(InterviewRecording).count()
    total_questions = db.query(InterviewQuestion).count()

    # 今日活跃用户数（今日有对话的用户）
    active_users_today = (
        db.query(Conversation.user_id)
        .filter(Conversation.updated_at >= today_start)
        .distinct()
        .count()
    )

    # Agent 调用统计
    total_agent_calls = db.query(AgentLog).count()

    # 平均延迟
    from sqlalchemy import func
    avg_latency = db.query(func.avg(AgentLog.latency_ms)).scalar()

    return APIResponse(
        data=DashboardStats(
            total_users=total_users,
            total_conversations=total_conversations,
            total_resumes=total_resumes,
            total_recordings=total_recordings,
            total_questions=total_questions,
            active_users_today=active_users_today,
            total_agent_calls=total_agent_calls,
            avg_latency_ms=round(avg_latency, 2) if avg_latency else None,
        ),
    )


@router.get(
    "/users",
    response_model=APIResponse[dict],
    summary="获取用户列表（管理员）",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    role: str | None = Query(default=None),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员查看所有用户列表"""
    query = db.query(User)
    if keyword:
        query = query.filter((User.username.contains(keyword)) | (User.email.contains(keyword)))
    if role:
        try:
            query = query.filter(User.role == UserRole(role))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效角色")

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return APIResponse(
        data={
            "items": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role.value,
                    "created_at": u.created_at.isoformat(),
                    "updated_at": u.updated_at.isoformat() if getattr(u, "updated_at", None) else None,
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    )


@router.put(
    "/users/{user_id}/role",
    response_model=APIResponse[dict],
    summary="修改用户角色",
)
async def update_user_role(
    user_id: int,
    role: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员修改用户角色"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的角色。可选: {[r.value for r in UserRole]}",
        )

    user.role = new_role
    db.commit()

    return APIResponse(
        data={"id": user.id, "role": user.role.value},
        message="角色更新成功",
    )


@router.get(
    "/agent-logs",
    response_model=APIResponse[list[dict]],
    summary="获取 Agent 调用日志",
)
async def get_agent_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    agent_name: str | None = Query(default=None, description="按 Agent 名称筛选"),
    status_filter: str | None = Query(default=None, description="按状态筛选"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员查看 Agent 调用日志"""
    query = db.query(AgentLog)

    if agent_name:
        query = query.filter(AgentLog.agent_name == agent_name)
    if status_filter:
        query = query.filter(AgentLog.status == status_filter)

    logs = (
        query
        .order_by(AgentLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return APIResponse(
        data=[
            {
                "id": log.id,
                "conversation_id": log.conversation_id,
                "agent_name": log.agent_name,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "latency_ms": log.latency_ms,
                "status": log.status,
                "error_msg": log.error_msg,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    )


@router.get(
    "/agent-stats",
    response_model=APIResponse[list[dict]],
    summary="获取 Agent 汇总统计",
)
async def get_agent_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """按 Agent 聚合调用次数、成功率和平均耗时"""
    from sqlalchemy import case, func

    rows = (
        db.query(
            AgentLog.agent_name,
            func.count(AgentLog.id).label("calls"),
            func.avg(AgentLog.latency_ms).label("avg_latency"),
            func.sum(case((AgentLog.status == "success", 1), else_=0)).label("success_calls"),
        )
        .group_by(AgentLog.agent_name)
        .all()
    )
    data = []
    for name, calls, avg_latency, success_calls in rows:
        success_rate = round((success_calls or 0) * 100 / calls, 1) if calls else 0
        data.append({
            "agent_name": name,
            "calls": calls,
            "success_rate": success_rate,
            "avg_latency_ms": round(avg_latency or 0, 2),
        })
    return APIResponse(data=data)


@router.get(
    "/knowledge/stats",
    response_model=APIResponse[dict],
    summary="获取知识库统计",
)
async def get_knowledge_stats(
    admin: User = Depends(get_admin_user),
):
    """统计 knowledge_base 文件和 ChromaDB 向量数量"""
    from app.config import BASE_DIR

    kb_dir = BASE_DIR.parent / "knowledge_base"
    files = list(kb_dir.rglob("*")) if kb_dir.exists() else []
    docs = [p for p in files if p.is_file() and p.suffix.lower() in {".md", ".txt", ".pdf"}]
    vector_count = 0
    try:
        from app.services.rag_service import RAGService

        stats = await RAGService().get_collection_stats()
        vector_count = stats.get("count", 0)
    except Exception:
        pass

    return APIResponse(data={
        "file_count": len(docs),
        "vector_count": vector_count,
        "kb_dir": str(kb_dir),
    })


@router.post(
    "/knowledge/upload",
    response_model=APIResponse[dict],
    summary="上传知识库文档并重新入库",
)
async def upload_knowledge(
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_user),
):
    """上传 .md/.txt/.pdf 文档到 knowledge_base 并触发加载。"""
    from app.config import BASE_DIR
    from app.services.knowledge_loader import KnowledgeLoader

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".md", ".txt", ".pdf"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .md、.txt、.pdf")

    kb_dir = BASE_DIR.parent / "knowledge_base" / "uploaded"
    kb_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "knowledge.txt").name
    target = kb_dir / safe_name
    with target.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    loaded = KnowledgeLoader().load_all()
    return APIResponse(
        data={"file": str(target), "loaded": loaded},
        message="知识库上传并入库完成",
    )
