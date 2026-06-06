"""
AI 面试会话与轮次 ORM 模型
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InterviewSession(Base):
    """AI 面试会话表"""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="面试会话ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, comment="面试标题")
    target_position: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="目标岗位"
    )
    interview_type: Mapped[str] = mapped_column(
        String(64), default="technical", nullable=False, comment="面试类型"
    )
    difficulty: Mapped[str] = mapped_column(
        String(32), default="medium", nullable=False, comment="难度"
    )
    question_count: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False, comment="题目数量"
    )
    answer_mode: Mapped[str] = mapped_column(
        String(32), default="text", nullable=False, comment="回答方式"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True, comment="会话状态"
    )
    total_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="面试总分"
    )
    report: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="面试报告"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始时间"
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    user: Mapped["User"] = relationship("User", back_populates="interview_sessions")
    turns: Mapped[list["InterviewTurn"]] = relationship(
        "InterviewTurn",
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="InterviewTurn.question_index",
    )

    def __repr__(self) -> str:
        return f"<InterviewSession(id={self.id}, status={self.status})>"


class InterviewTurn(Base):
    """AI 面试问答轮次表"""

    __tablename__ = "interview_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "question_index", name="uq_interview_turn_session_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="轮次ID")
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="面试会话ID",
    )
    question_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="题目序号"
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="面试问题")
    answer_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="文字回答"
    )
    answer_audio_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="音频回答地址"
    )
    answer_duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="回答时长（秒）"
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True, comment="轮次评分")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="轮次反馈")
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="改进建议")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="回答时间"
    )

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="turns"
    )

    def __repr__(self) -> str:
        return f"<InterviewTurn(id={self.id}, question_index={self.question_index})>"
