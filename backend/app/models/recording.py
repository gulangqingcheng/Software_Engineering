"""
面试录音表 ORM 模型
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RecordingStatus(str, enum.Enum):
    """录音处理状态枚举"""
    UPLOADED = "uploaded"          # 已上传
    TRANSCRIBING = "transcribing"  # 转写中
    TRANSCRIBED = "transcribed"    # 已转写
    ANALYZING = "analyzing"        # 分析中
    COMPLETED = "completed"        # 分析完成
    FAILED = "failed"              # 处理失败


class InterviewRecording(Base):
    """面试录音表"""
    __tablename__ = "interview_recordings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="录音ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    file_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="音频文件存储路径"
    )
    file_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="原始文件名"
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="音频时长（秒）"
    )
    transcript: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="ASR 转写文本"
    )
    analysis_result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="分析结果（JSON格式），包含语速、流畅度、关键信息等"
    )
    collected_questions: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="收集到的面试题（JSON列表）"
    )
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus),
        default=RecordingStatus.UPLOADED,
        nullable=False,
        comment="处理状态",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    # ── 关联关系 ──
    user: Mapped["User"] = relationship("User", back_populates="recordings")

    def __repr__(self) -> str:
        return f"<InterviewRecording(id={self.id}, file_name={self.file_name})>"
