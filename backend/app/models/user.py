"""
用户表 ORM 模型
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="用户名"
    )
    password_hash: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="密码哈希（bcrypt）"
    )
    email: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, comment="电子邮箱"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="头像URL"
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
        comment="用户角色：user / admin",
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
    profile: Mapped["UserProfile | None"] = relationship(
        "UserProfile", back_populates="user", uselist=False, lazy="selectin",
        cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", lazy="selectin"
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume", back_populates="user", lazy="selectin"
    )
    recordings: Mapped[list["InterviewRecording"]] = relationship(
        "InterviewRecording", back_populates="user", lazy="selectin"
    )
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
