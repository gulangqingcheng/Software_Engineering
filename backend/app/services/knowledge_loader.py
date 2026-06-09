"""
知识库文档加载器
扫描 knowledge_base/ 目录，智能分块，批量向量化写入 ChromaDB + MySQL
"""

import logging
import re
import uuid
from pathlib import Path

from app.config import settings, BASE_DIR
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    """
    知识库文档加载器

    功能：
    1. 扫描 knowledge_base/ 下的 .md / .txt 文件
    2. 智能分块（按段落 + 固定长度兜底）
    3. 批量向量化写入 ChromaDB
    4. 原文元数据写入 MySQL interview_guide 表
    """

    # 分块参数
    CHUNK_SIZE = 500       # 每块最大字符数
    CHUNK_OVERLAP = 50     # 重叠字符数（保持上下文连贯）
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}

    def __init__(self, kb_dir: str | None = None):
        """
        Args:
            kb_dir: 知识库根目录，默认为项目根目录下的 knowledge_base/
        """
        if kb_dir:
            self.kb_dir = Path(kb_dir)
        else:
            self.kb_dir = BASE_DIR.parent / "knowledge_base"

    def load_all(self) -> dict[str, int]:
        """
        扫描并加载所有知识文档

        Returns:
            dict: {"total_files": X, "total_chunks": Y, "categories": {...}}
        """
        stats = {"total_files": 0, "total_chunks": 0, "categories": {}}

        if not self.kb_dir.exists():
            logger.warning(f"[知识库] 目录不存在: {self.kb_dir}")
            return stats

        # 复用同一个 RAGService 实例，避免多 PersistentClient 锁冲突
        from app.services.rag_service import RAGService
        self._rag = RAGService()

        # 遍历所有支持的文件
        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in self.kb_dir.rglob(f"*{ext}"):
                # 跳过 README 文件
                if file_path.name.lower().startswith("readme"):
                    continue
                # 跳过 .gitkeep
                if file_path.name == ".gitkeep":
                    continue

                try:
                    file_stats = self._process_file(file_path)
                    stats["total_files"] += 1
                    stats["total_chunks"] += file_stats["chunks"]
                    category = file_stats.get("category", "unknown")
                    stats["categories"][category] = (
                        stats["categories"].get(category, 0) + file_stats["chunks"]
                    )
                except Exception as e:
                    logger.error(f"[知识库] 处理文件失败 {file_path}: {e}")

        logger.info(
            f"[知识库] 加载完成: {stats['total_files']} 个文件, "
            f"{stats['total_chunks']} 个文档块"
        )
        return stats

    def _process_file(self, file_path: Path) -> dict:
        """
        处理单个文件：读取 -> 清洗 -> 分块 -> 入库

        Returns:
            dict: {"chunks": int, "category": str}
        """
        logger.info(f"[知识库] 正在处理: {file_path.name}")

        # 1. 读取文件
        content = self._read_file(file_path)

        # 2. 清洗文本
        content = self._clean_text(content)

        if not content.strip():
            logger.warning(f"[知识库] 文件内容为空，跳过: {file_path.name}")
            return {"chunks": 0, "category": ""}

        # 3. 智能分块
        chunks = self._split_text(content)

        if not chunks:
            return {"chunks": 0, "category": ""}

        # 4. 构造元数据
        category = self._infer_category(file_path, content)
        metadatas = [{
            "source": file_path.name,
            "category": category,
            "relative_path": str(file_path.relative_to(self.kb_dir)),
        } for _ in chunks]

        # 5. 生成唯一 ID
        ids = [uuid.uuid4().hex for _ in chunks]

        # 6. 异步写入 ChromaDB（此处收集数据，由调用方批量处理）
        # 注意：此方法在 lifespan 中同步调用，
        # ChromaDB 的 add 操作本身是同步的
        self._write_to_chromadb(chunks, metadatas, ids)

        logger.info(f"[知识库] {file_path.name}: {len(chunks)} 个文档块已入库")
        return {"chunks": len(chunks), "category": category}

    def _read_file(self, file_path: Path) -> str:
        """按文件类型读取知识库文档文本。"""
        if file_path.suffix.lower() == ".pdf":
            try:
                import pdfplumber

                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                return "\n\n".join(text_parts)
            except Exception as e:
                logger.error(f"[知识库] PDF 解析失败 {file_path}: {e}")
                return ""

        return file_path.read_text(encoding="utf-8")

    def _clean_text(self, text: str) -> str:
        """清洗文本：去除多余空行、特殊字符等"""
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 去除连续空行（保留最多一个空行）
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行首行尾空白
        text = "\n".join(line.strip() for line in text.split("\n"))
        return text.strip()

    def _split_text(self, text: str) -> list[str]:
        """
        智能分块：优先按段落切分，段落过长再按字符切分

        策略：
        1. 按 \n\n (空行) 分段
        2. 段落 < CHUNK_SIZE 则合并
        3. 单段落 > CHUNK_SIZE 则按字符切分
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 当前块 + 新段落超长，先保存当前块
            if current_chunk and len(current_chunk) + len(para) + 2 > self.CHUNK_SIZE:
                chunks.append(current_chunk.strip())
                # 保留重叠部分
                if len(current_chunk) > self.CHUNK_OVERLAP:
                    current_chunk = current_chunk[-self.CHUNK_OVERLAP:]
                else:
                    current_chunk = ""

            # 单段落超长，需要按字符切分
            if len(para) > self.CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                # 按字符切分（带重叠）
                for i in range(0, len(para), self.CHUNK_SIZE - self.CHUNK_OVERLAP):
                    piece = para[i: i + self.CHUNK_SIZE].strip()
                    if piece:
                        chunks.append(piece)
                continue

            # 合并到当前块
            if current_chunk:
                current_chunk = f"{current_chunk}\n\n{para}"
            else:
                current_chunk = para

        # 保存最后一块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _infer_category(self, file_path: Path, content: str) -> str:
        """
        从文件路径推断分类

        目录结构：
        knowledge_base/
        ├── interview_guide/   -> category = "面试技巧"
        ├── question_bank/     -> category = "题库"
        └── resume_templates/  -> category = "简历模板"
        """
        dir_name = file_path.parent.name

        category_map = {
            "interview_guide": "面试技巧",
            "question_bank": "题库",
            "resume_templates": "简历模板",
            "company_info": "企业信息",
            "templates": "模板",
            "career_guide": "职业规划",
        }

        return category_map.get(dir_name, dir_name)

    def _write_to_chromadb(
        self,
        chunks: list[str],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        """写入 ChromaDB（手动计算 BGE 向量后传入）"""
        try:
            # 直接使用 EmbeddingService 单例，不绕路通过 RAGService
            embeddings = EmbeddingService().encode(
                chunks, normalize=True,
            )
            self._rag.collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as e:
            import traceback
            logger.error(f"[知识库] ChromaDB 写入失败: {e}\n{traceback.format_exc()}")
            raise
