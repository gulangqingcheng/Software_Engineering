"""
面试题库表 ORM 模型
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QuestionCategory(str, enum.Enum):
    """题目分类枚举"""
    ALGORITHM = "algorithm"            # 算法题
    SYSTEM_DESIGN = "system_design"    # 系统设计
    FRONTEND = "frontend"              # 前端
    BACKEND = "backend"                # 后端
    DATABASE = "database"              # 数据库
    NETWORK = "network"                # 网络
    BEHAVIORAL = "behavioral"          # 行为面试
    PROJECT = "project"                # 项目经验
    GENERAL = "general"                # 综合


class QuestionDifficulty(str, enum.Enum):
    """题目难度枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionSource(str, enum.Enum):
    """题目来源枚举"""
    SYSTEM = "system"          # 系统内置
    AI_GENERATED = "ai_generated"  # AI 生成
    USER_UPLOADED = "user_uploaded"  # 用户上传
    COLLECTED = "collected"    # 从录音中收集


class InterviewQuestion(Base):
    """面试题库表"""
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="题目ID")
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属用户ID；为空表示公共题库",
    )
    question: Mapped[str] = mapped_column(
        Text, nullable=False, comment="面试题目内容"
    )
    category: Mapped[QuestionCategory] = mapped_column(
        Enum(QuestionCategory),
        default=QuestionCategory.GENERAL,
        nullable=False,
        index=True,
        comment="题目分类",
    )
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty),
        default=QuestionDifficulty.MEDIUM,
        nullable=False,
        comment="难度等级",
    )
    source: Mapped[QuestionSource] = mapped_column(
        Enum(QuestionSource),
        default=QuestionSource.SYSTEM,
        nullable=False,
        comment="题目来源",
    )
    reference_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="参考答案"
    )
    tags: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="标签（JSON数组）"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="使用次数"
    )
    embedding_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="ChromaDB 向量ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<InterviewQuestion(id={self.id}, category={self.category})>"
