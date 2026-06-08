from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.interview import router as interview_router
from app.config import settings
from app.database import Base, engine
from app.models import (  # noqa: F401
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=f"{settings.APP_NAME} Lite",
    version=settings.APP_VERSION,
    description="AI interview demo service with auth, scoring, and report APIs.",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code=500,
            message="服务端内部错误",
            detail=str(exc) if settings.DEBUG else "请稍后重试",
        ).model_dump(),
    )


app.include_router(auth_router)
app.include_router(interview_router)


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "mode": "lite",
        "version": settings.APP_VERSION,
    }
