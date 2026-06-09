"""
简历模板查重检测服务
通过向量相似度计算检测简历内容是否来自模板
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PlagiarismChecker:
    """
    模板查重检测服务

    功能：
    1. 将简历内容分块向量化
    2. 与 ChromaDB 模板库（category="简历模板"）进行相似度对比
    3. 返回加权查重得分和相似来源
    """

    # 查重阈值：分数 > 70 视为疑似模板
    SUSPICIOUS_THRESHOLD = 70
    # RAG 检索相似度阈值（0.5 较灵敏，避免漏检）
    SEARCH_THRESHOLD = 0.5
    # 最小块长度（低于此值的段落跳过，减少噪音）
    MIN_CHUNK_LENGTH = 50

    def __init__(self):
        self._rag_service = None

    def _get_rag_service(self):
        """延迟初始化 RAGService，避免循环导入"""
        if self._rag_service is None:
            from app.services.rag_service import RAGService
            self._rag_service = RAGService()
        return self._rag_service

    def _split_into_chunks(self, text: str, min_length: int = 50) -> list[str]:
        """
        将文本按段落分块

        Args:
            text: 原始文本
            min_length: 最小块长度（低于此值的块将被过滤或合并）

        Returns:
            文本块列表
        """
        if not text or not text.strip():
            return []

        # 按空行分段
        raw_paragraphs = text.split("\n\n")

        chunks: list[str] = []
        buffer = ""

        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(para) >= min_length:
                # 缓冲区中有残余文本，先加入
                if buffer:
                    merged = (buffer + "\n" + para).strip()
                    chunks.append(merged)
                    buffer = ""
                else:
                    chunks.append(para)
            else:
                # 短段落：累加到缓冲区
                if buffer:
                    buffer = buffer + "\n" + para
                else:
                    buffer = para

                # 缓冲区累积到足够长度时作为一个块
                if len(buffer) >= min_length:
                    chunks.append(buffer.strip())
                    buffer = ""

        # 处理剩余缓冲区
        if buffer.strip():
            chunks.append(buffer.strip())

        return chunks

    async def check(self, text: str) -> dict[str, Any]:
        """
        检测简历内容与模板库的相似度

        Args:
            text: 简历文本内容

        Returns:
            dict: {
                "score": 85.5,              # 查重得分（0-100，越高越可能是模板）
                "similar_sources": [
                    {"name": "经典模板A", "similarity": 0.85},
                ],
                "is_suspicious": True,      # 是否疑似模板
            }
        """
        if not text or not text.strip():
            return {"score": 0.0, "similar_sources": [], "is_suspicious": False}

        chunks = self._split_into_chunks(text, self.MIN_CHUNK_LENGTH)
        if not chunks:
            return {"score": 0.0, "similar_sources": [], "is_suspicious": False}

        rag = self._get_rag_service()

        # 收集所有块的最高相似度匹配
        all_matches: list[dict[str, Any]] = []
        chunk_weights: list[float] = []  # 每个匹配对应块的长度权重
        seen_sources: set[str] = set()   # 去重：同一条源文档不重复计数

        for chunk in chunks:
            try:
                results = await rag.search(
                    query=chunk,
                    top_k=3,
                    threshold=self.SEARCH_THRESHOLD,
                )
            except Exception as e:
                logger.warning(f"[查重] RAG 检索失败: {e}")
                results = []

            for r in results:
                # 只取简历模板类别的结果
                category = r.get("metadata", {}).get("category", "")
                if category != "简历模板":
                    continue

                source_id = r.get("id", "")
                source_key = f"{source_id}_{r.get('content', '')[:30]}"
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)

                source_name = r.get("metadata", {}).get(
                    "source", r.get("metadata", {}).get("relative_path", "未知模板")
                )
                similarity = r.get("score", 0)

                all_matches.append({
                    "name": source_name,
                    "similarity": round(similarity, 4),
                })
                chunk_weights.append(len(chunk))

        if not all_matches:
            return {"score": 0.0, "similar_sources": [], "is_suspicious": False}

        # 加权平均：相似度按块长度加权
        total_weight = sum(chunk_weights)
        weighted_score = sum(
            m["similarity"] * w for m, w in zip(all_matches, chunk_weights)
        ) / total_weight if total_weight > 0 else 0

        score = min(weighted_score * 100, 100)

        # 按相似度降序排列，取 top 5
        all_matches.sort(key=lambda x: x["similarity"], reverse=True)
        similar_sources = all_matches[:5]

        return {
            "score": round(score, 2),
            "similar_sources": similar_sources,
            "is_suspicious": score > self.SUSPICIOUS_THRESHOLD,
        }

    async def add_template(self, name: str, content: str) -> str:
        """
        向模板库中添加简历模板

        Args:
            name: 模板名称
            content: 模板内容

        Returns:
            str: 添加的模板ID
        """
        rag = self._get_rag_service()
        import uuid
        doc_id = f"tpl_{uuid.uuid4().hex[:12]}"
        try:
            ids = await rag.add_documents(
                documents=[content],
                metadatas=[{
                    "template_name": name,
                    "category": "简历模板",
                    "source": name,
                }],
                ids=[doc_id],
            )
            return ids[0] if ids else doc_id
        except Exception as e:
            logger.error(f"[查重] 添加模板失败: {e}")
            return doc_id
