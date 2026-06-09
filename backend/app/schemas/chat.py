"""
对话相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


# ── 消息 ──
class MessageCreateRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1, description="消息内容")
    message_type: str = Field(default="text", description="消息类型：text / voice / image")


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    conversation_id: int
    role: str
    content: str
    agent_name: str | None = None
    message_type: str
    file_url: str | None = None
    file_name: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def fill_file_fields(cls, data):
        if isinstance(data, dict):
            metadata = data.get("metadata") or data.get("metadata_") or {}
            if isinstance(metadata, dict):
                data.setdefault("file_url", metadata.get("file_url"))
                data.setdefault("file_name", metadata.get("file_name"))
            return data

        metadata = getattr(data, "metadata_", None) or {}
        if isinstance(metadata, dict):
            data.file_url = metadata.get("file_url")
            data.file_name = metadata.get("file_name")
        return data

    model_config = {"from_attributes": True}


# ── 会话 ──
class ConversationCreateRequest(BaseModel):
    """创建会话请求"""
    title: str = Field(default="新对话", description="会话标题")
    agent_type: str = Field(default="orchestrator", description="Agent类型")


class ConversationResponse(BaseModel):
    """会话响应"""
    id: int
    user_id: int
    title: str
    agent_type: str
    status: str
    last_message: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    """会话详情响应（含消息列表）"""
    messages: list[MessageResponse] = Field(default_factory=list, description="消息列表")


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    conversations: list[ConversationResponse]
    total: int
