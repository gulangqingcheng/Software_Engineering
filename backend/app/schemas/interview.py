"""
AI 面试相关 Pydantic Schema
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator


class InterviewSessionCreateRequest(BaseModel):
    """创建 AI 面试会话请求"""

    title: str | None = Field(default=None, min_length=1, max_length=256, description="面试标题")
    target_position: str = Field(..., min_length=1, max_length=128, description="目标岗位")
    interview_type: str = Field(default="technical", min_length=1, max_length=64, description="面试类型")
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$", description="难度")
    question_count: int = Field(default=5, ge=1, le=20, description="题目数量")
    answer_mode: str = Field(default="text", pattern="^(text|audio|mixed)$", description="回答方式")


class InterviewAnswerRequest(BaseModel):
    """提交面试回答请求"""

    answer_text: str | None = Field(default=None, max_length=20000, description="文字回答")
    answer_audio_url: str | None = Field(default=None, max_length=512, description="音频回答地址")
    answer_duration_seconds: int | None = Field(default=None, ge=0, description="回答时长（秒）")

    @model_validator(mode="after")
    def validate_answer(self) -> Self:
        if not (self.answer_text and self.answer_text.strip()) and not self.answer_audio_url:
            raise ValueError("answer_text 和 answer_audio_url 至少提供一项")
        return self


class InterviewTurnResponse(BaseModel):
    """面试轮次响应"""

    id: int
    session_id: int
    question_index: int
    question: str
    answer_text: str | None = None
    answer_audio_url: str | None = None
    answer_duration_seconds: int | None = None
    score: float | None = None
    feedback: str | None = None
    suggestion: str | None = None
    created_at: datetime
    answered_at: datetime | None = None

    model_config = {"from_attributes": True}


class InterviewSessionResponse(BaseModel):
    """面试会话响应"""

    id: int
    user_id: int
    title: str
    target_position: str
    interview_type: str
    difficulty: str
    question_count: int
    answer_mode: str
    status: str
    total_score: float | None = None
    report: dict | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewSessionDetailResponse(InterviewSessionResponse):
    """包含问答轮次的面试会话详情"""

    turns: list[InterviewTurnResponse] = Field(default_factory=list)


class InterviewTurnPerformance(BaseModel):
    """报告中的单轮表现"""

    question_index: int
    question: str
    score: float
    feedback: str
    suggestion: str


class InterviewReportResponse(BaseModel):
    """面试报告响应"""

    session_id: int
    total_score: float
    status: str
    summary: str
    turn_performance: list[InterviewTurnPerformance] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    generated_at: datetime
