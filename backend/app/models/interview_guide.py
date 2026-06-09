"""
面试宝典知识库表 ORM 模型
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InterviewGuide(Base):
    """面试宝典知识库表 - 存储RAG检索的文档片段"""
    __tablename__ = "interview_guide"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="文档ID")
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True, comment="文档标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="文档内容（文本块）"
    )
    category: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="分类：算法/系统设计/前端/后端等"
    )
    source: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="来源：文件名或URL"
    )
    chunk_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="分块ID"
    )
    embedding_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="ChromaDB 向量ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<InterviewGuide(id={self.id}, title={self.title})>"
