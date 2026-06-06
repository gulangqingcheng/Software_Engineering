"""
数据校验 Schema 包
"""

from app.schemas.common import APIResponse, ErrorResponse, PaginatedResponse
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.schemas.chat import (
    MessageCreateRequest,
    MessageResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
)
from app.schemas.resume import (
    ResumeResponse,
    ResumeEvaluationResponse,
    ResumeListResponse,
)
from app.schemas.recording import (
    RecordingResponse,
    RecordingAnalysisResponse,
    RecordingListResponse,
)
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewReportResponse,
    InterviewSessionCreateRequest,
    InterviewSessionDetailResponse,
    InterviewSessionResponse,
    InterviewTurnResponse,
)

__all__ = [
    # 通用
    "APIResponse",
    "ErrorResponse",
    "PaginatedResponse",
    # 用户
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
    "UserUpdateRequest",
    # 对话
    "MessageCreateRequest",
    "MessageResponse",
    "ConversationCreateRequest",
    "ConversationResponse",
    "ConversationDetailResponse",
    "ConversationListResponse",
    # 简历
    "ResumeResponse",
    "ResumeEvaluationResponse",
    "ResumeListResponse",
    # 录音
    "RecordingResponse",
    "RecordingAnalysisResponse",
    "RecordingListResponse",
    # AI 面试
    "InterviewAnswerRequest",
    "InterviewReportResponse",
    "InterviewSessionCreateRequest",
    "InterviewSessionDetailResponse",
    "InterviewSessionResponse",
    "InterviewTurnResponse",
]
