"""
API 路由包
"""

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.resume import router as resume_router
from app.api.recording import router as recording_router
from app.api.question import router as question_router
from app.api.admin import router as admin_router
from app.api.profile import router as profile_router
from app.api.interview import router as interview_router

__all__ = [
    "auth_router",
    "chat_router",
    "resume_router",
    "recording_router",
    "question_router",
    "admin_router",
    "profile_router",
    "interview_router",
]
