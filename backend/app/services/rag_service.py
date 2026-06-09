"""
RAG 检索服务
基于 ChromaDB 的向量存储和语义检索
使用本地 BGE Embedding 模型进行向量化
"""

import logging
import os
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)


class _NoOpEmbeddingFunction:
    """
    空操作 EmbeddingFunction，阻止 ChromaDB 下载默认模型 all-MiniLM-L6-v2。
    本项目所有向量均手动计算（BGE）后传入，此函数永远不会被实际调用。
    """

    def name(self) -> str:
        return "default"

    def __call__(self, input: list[str]) -> list[list[float]]:
        logger.warning("[RAG] _NoOpEmbeddingFunction 被意外调用！")
        return [[0.0] * 384 for _ in input]


class RAGService:
    """
    RAG（检索增强生成）服务

    功能：
    1. 文档向量化存储（手动 BGE 编码 + ChromaDB 存储）
    2. 语义相似度检索
    3. 文档删除和更新
    """

    def __init__(self):
        # 确保持久化目录存在
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self.collection_name = settings.CHROMA_COLLECTION_NAME
        self._collection = None
        self._embedding_service = None

    def _get_embedding_service(self):
        """懒加载 EmbeddingService"""
        if self._embedding_service is None:
            from app.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def collection(self):
        """懒加载获取或创建 Collection（传入空操作 EF，手动传入向量）"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=_NoOpEmbeddingFunction(),
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        """
        添加文档到向量库（手动 BGE 编码后写入 ChromaDB）
        """
        if ids is None:
            ids = [uuid.uuid4().hex for _ in documents]

        # 手动计算向量
        embeddings = self._get_embedding_service().encode(documents, normalize=True)

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return ids

    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        语义检索（手动 BGE 编码查询后检索）
        """
        threshold = threshold or settings.CHROMA_SIMILARITY_THRESHOLD

        # 手动计算查询向量
        query_embedding = self._get_embedding_service().encode_single(query, normalize=True)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        output = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc_content = results["documents"][0][i] if results["documents"] else ""
                doc_metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                doc_distance = results["distances"][0][i] if results["distances"] else 0

                doc_score = 1 - doc_distance

                if doc_score < threshold:
                    continue

                output.append({
                    "id": doc_id,
                    "content": doc_content,
                    "metadata": doc_metadata,
                    "score": round(doc_score, 4),
                })

        return output

    async def delete_documents(self, ids: list[str]) -> None:
        """从向量库中删除文档"""
        self.collection.delete(ids=ids)

    async def delete_collection(self) -> None:
        """删除整个 Collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self._collection = None
        except Exception:
            pass

    async def reset_collection(self) -> None:
        """重置 Collection（删除后重建）"""
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self._collection = None
        _ = self.collection

    async def get_collection_stats(self) -> dict[str, Any]:
        """获取 Collection 统计信息"""
        count = self.collection.count()
        return {
            "name": self.collection_name,
            "document_count": count,
        }
