"""
消息记录表 ORM 模型
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, enum.Enum):
    """消息类型枚举"""
    TEXT = "text"              # 纯文本消息
    VOICE = "voice"            # 语音消息
    IMAGE = "image"            # 图片消息
    FILE = "file"              # 文件消息
    TOOL_CALL = "tool_call"    # Agent工具调用记录
    SYSTEM_NOTICE = "system_notice"  # 系统通知


class Message(Base):
    """消息记录表"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="消息ID")
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话ID",
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="消息角色：user / assistant / system"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息内容"
    )
    agent_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="处理该消息的Agent名称"
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        default="text",
        nullable=False,
        comment="消息类型",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="扩展元数据（JSON格式）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    # ── 关联关系 ──
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"
