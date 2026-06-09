"""
简历相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    """简历响应"""
    id: int
    user_id: int
    file_name: str
    file_path: str
    parsed_content: str | None = None
    evaluation_result: dict | None = None
    plagiarism_score: float | None = None
    violation_words: dict | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeEvaluationResponse(BaseModel):
    """简历评估结果响应"""
    resume_id: int = Field(..., description="简历ID")
    overall_score: float = Field(..., description="综合评分（0-100）")
    strengths: list[str] = Field(default_factory=list, description="亮点")
    weaknesses: list[str] = Field(default_factory=list, description="不足")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
    plagiarism_score: float | None = Field(default=None, description="模板查重得分")
    violation_words: list[str] | None = Field(default=None, description="违禁词列表")
    detailed_analysis: str | None = Field(default=None, description="详细分析文本")


class ResumeListResponse(BaseModel):
    """简历列表响应"""
    resumes: list[ResumeResponse]
    total: int
