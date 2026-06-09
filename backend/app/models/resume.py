"""
简历表 ORM 模型
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResumeStatus(str, enum.Enum):
    """简历处理状态枚举"""
    UPLOADED = "uploaded"        # 已上传
    PARSING = "parsing"          # 解析中
    PARSED = "parsed"            # 已解析
    EVALUATING = "evaluating"    # 评估中
    COMPLETED = "completed"      # 评估完成
    FAILED = "failed"            # 处理失败


class Resume(Base):
    """简历表"""
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="简历ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    file_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="文件存储路径"
    )
    file_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="原始文件名"
    )
    parsed_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="解析后的文本内容"
    )
    evaluation_result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="评估结果（JSON格式）"
    )
    plagiarism_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="模板查重得分（0-100）"
    )
    violation_words: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="检测到的违禁词列表"
    )
    status: Mapped[ResumeStatus] = mapped_column(
        Enum(ResumeStatus),
        default=ResumeStatus.UPLOADED,
        nullable=False,
        comment="处理状态",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    # ── 关联关系 ──
    user: Mapped["User"] = relationship("User", back_populates="resumes")

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, file_name={self.file_name})>"
