"""
FastAPI 应用入口
注册所有路由、中间件、异常处理器
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import (
    admin_router,
    auth_router,
    chat_router,
    interview_router,
    profile_router,
    question_router,
    recording_router,
    resume_router,
)
from app.config import settings
from app.database import Base, engine
from app.models import (  # noqa: F401 确保所有 ORM 模型注册到 Base.metadata
    AgentLog,
    Conversation,
    InterviewGuide,
    InterviewQuestion,
    InterviewRecording,
    InterviewSession,
    InterviewTurn,
    Message,
    Resume,
    User,
    UserProfile,
)
from app.schemas.common import ErrorResponse


def ensure_schema_compatibility() -> None:
    """Apply small additive schema updates for existing demo databases."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("interview_questions")}
    if "user_id" not in columns:
        dialect = engine.dialect.name
        if dialect == "mysql":
            ddl = "ALTER TABLE interview_questions ADD COLUMN user_id INT NULL, ADD INDEX ix_interview_questions_user_id (user_id)"
        else:
            ddl = "ALTER TABLE interview_questions ADD COLUMN user_id INTEGER NULL"
        with engine.begin() as conn:
            conn.execute(text(ddl))

    profile_columns = {col["name"] for col in inspector.get_columns("user_profiles")}
    profile_extra_columns = {
        "education_level": "VARCHAR(64)",
        "degree": "VARCHAR(64)",
        "graduation_year": "VARCHAR(32)",
        "target_position": "VARCHAR(128)",
        "target_city": "VARCHAR(128)",
        "skills": "VARCHAR(512)",
        "certificates": "VARCHAR(512)",
        "internship_experience": "VARCHAR(1024)",
    }
    with engine.begin() as conn:
        for column, column_type in profile_extra_columns.items():
            if column not in profile_columns:
                if engine.dialect.name == "mysql":
                    conn.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {column} {column_type} NULL"))
                else:
                    conn.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {column} TEXT NULL"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时创建必要的目录和初始化资源
    """
    # ── 启动时执行 ──
    # 确保上传目录存在
    upload_dirs = [
        os.path.join(settings.UPLOAD_DIR, "resumes"),
        os.path.join(settings.UPLOAD_DIR, "recordings"),
        os.path.join(settings.UPLOAD_DIR, "temp"),
        os.path.join(settings.UPLOAD_DIR, "avatars"),
    ]
    for dir_path in upload_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[启动] 确保目录存在: {dir_path}")
    os.makedirs("artifacts", exist_ok=True)
    print("[启动] 确保目录存在: artifacts")

    # 确保 ChromaDB 持久化目录存在
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    print(f"[启动] ChromaDB 持久化目录: {settings.CHROMA_PERSIST_DIR}")

    # 自动创建数据库表（如不存在）
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    print("[启动] 数据库表检查/创建完成")

    # ── 加载知识库到 ChromaDB RAG ──
    try:
        import shutil
        from app.services.rag_service import RAGService
        from app.services.knowledge_loader import KnowledgeLoader

        # 清空旧数据，避免 embedding_function 配置冲突
        if os.path.exists(settings.CHROMA_PERSIST_DIR):
            shutil.rmtree(settings.CHROMA_PERSIST_DIR, ignore_errors=True)
            print("[启动] 已清理旧的 ChromaDB 数据")

        # 创建 RAGService（内部会自动重建持久化目录和 collection）
        rag = RAGService()

        # 加载知识库文档
        loader = KnowledgeLoader()
        loader._rag = rag  # 复用同一个 RAGService 实例
        kb_stats = loader.load_all()
        if kb_stats["total_chunks"] > 0:
            print(
                f"[启动] 知识库加载完成: "
                f"{kb_stats['total_files']} 个文件, "
                f"{kb_stats['total_chunks']} 个文档块"
            )
        else:
            print("[启动] 知识库为空，跳过加载 (请向 knowledge_base/ 添加 .md/.txt 文件)")
    except Exception as e:
        print(f"[启动] 知识库加载失败（不影响主功能）: {e}")

    print(f"[启动] {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"[启动] 环境: {settings.ENVIRONMENT}")
    print(f"[启动] LLM 模型: {settings.LLM_MODEL_NAME}")

    yield

    # ── 关闭时执行 ──
    print("[关闭] 应用正在关闭...")


# ── 创建 FastAPI 实例 ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="传智杯 AIGC 面试助手 - 后端 API 服务",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── CORS 中间件配置 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 全局异常处理器 ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，统一返回 ErrorResponse 格式"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code=500,
            message="服务器内部错误",
            detail=str(exc) if settings.DEBUG else "请稍后重试",
        ).model_dump(),
    )


# ── 注册路由 ──
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(resume_router)
app.include_router(recording_router)
app.include_router(question_router)
app.include_router(interview_router)
app.include_router(profile_router)
app.include_router(admin_router)

# ── 静态文件：上传文件访问 ──
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ── 健康检查端点 ──
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "llm_model": settings.LLM_MODEL_NAME,
    }


# ── 根路径 ──
@app.get("/", tags=["系统"])
async def root():
    """API 根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# ── 直接运行入口 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
