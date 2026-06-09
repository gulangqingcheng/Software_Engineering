"""
Agent 调用日志表 ORM 模型
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentLog(Base):
    """Agent 调用日志表 - 记录每次 Agent 调用的详细信息"""
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="日志ID")
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话ID",
    )
    agent_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Agent 名称"
    )
    input_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="输入 Token 数"
    )
    output_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="输出 Token 数"
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="调用延迟（毫秒）"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="success", nullable=False, comment="状态：success / failed / timeout"
    )
    error_msg: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息（当 status=failed 时）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    # ── 关联关系 ──
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="agent_logs"
    )

    def __repr__(self) -> str:
        return f"<AgentLog(id={self.id}, agent={self.agent_name}, status={self.status})>"
