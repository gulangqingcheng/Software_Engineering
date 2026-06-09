"""
录音相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RecordingResponse(BaseModel):
    """录音响应"""
    id: int
    user_id: int
    file_name: str
    duration_seconds: int | None = None
    transcript: str | None = None
    analysis_result: dict | None = None
    collected_questions: dict | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordingAnalysisResponse(BaseModel):
    """录音分析结果响应"""
    recording_id: int = Field(..., description="录音ID")
    transcript: str | None = Field(default=None, description="转写文本")
    duration_seconds: int = Field(..., description="时长（秒）")
    fluency_score: float | None = Field(default=None, description="流畅度评分")
    speech_rate: float | None = Field(default=None, description="语速（字/分钟）")
    key_points: list[str] = Field(default_factory=list, description="关键信息点")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
    collected_questions: list[dict] | None = Field(default=None, description="收集的面试题")


class RecordingListResponse(BaseModel):
    """录音列表响应"""
    recordings: list[RecordingResponse]
    total: int
