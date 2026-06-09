"""
对话会话表 ORM 模型
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConversationStatus(str, enum.Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"


class AgentType(str, enum.Enum):
    """Agent 类型枚举"""
    GENERAL = "general"          # 通用对话
    ORCHESTRATOR = "orchestrator"  # 主面试助手
    RESUME = "resume"              # 简历评估
    RECORDING = "recording"        # 录音分析
    QUESTION = "question"          # 面试题生成
    CAREER = "career"              # 职业规划


class Conversation(Base):
    """对话会话表"""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="会话ID")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID"
    )
    title: Mapped[str] = mapped_column(
        String(256), default="新对话", comment="会话标题"
    )
    agent_type: Mapped[str] = mapped_column(
        String(50),
        default="orchestrator",
        nullable=False,
        comment="使用的Agent类型",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        comment="会话状态",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    # ── 关联关系 ──
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan"
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"
