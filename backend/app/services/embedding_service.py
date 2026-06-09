"""
本地 Embedding 服务
基于 sentence-transformers 加载 BGE 模型，支持 GPU 加速
使用单例模式，全局共享一个模型实例，避免重复加载占用显存
"""

import logging
import os

import numpy as np

# 在导入 huggingface 相关库之前设置镜像源和缓存目录（国内环境必需）
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = r"F:\chuanzhibei\aigc\huggingface_cache"
# 启用 hf_transfer 加速下载（Rust 实现，比默认 HTTP 快约 30%）
# 注意：Windows 上 hf_transfer 可能在校验步骤卡住，如遇问题设为 "0"
if not os.environ.get("HF_HUB_ENABLE_HF_TRANSFER"):
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    本地 Embedding 服务

    - 模型: BAAI/bge-small-zh-v1.5 (512 维)
    - 设备: 自动检测 CUDA，无 GPU 时回退 CPU
    - 单例: 整个进程只加载一次模型
    """

    _instance: "EmbeddingService | None" = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

        # 检测设备
        import torch
        if settings.EMBEDDING_DEVICE == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"[Embedding] 使用 GPU: {gpu_name}")
            else:
                self.device = "cpu"
                logger.warning("[Embedding] GPU 不可用，回退 CPU")
        else:
            self.device = settings.EMBEDDING_DEVICE
            logger.info(f"[Embedding] 使用指定设备: {self.device}")

        # 加载模型
        logger.info(f"[Embedding] 正在加载模型: {self.model_name}")
        self.model = SentenceTransformer(
            self.model_name,
            device=self.device,
        )
        logger.info("[Embedding] 模型加载完成")

    def encode(
        self,
        texts: list[str],
        batch_size: int = 64,
        normalize: bool = True,
    ) -> list[list[float]]:
        """
        将文本列表编码为向量

        Args:
            texts: 待编码的文本列表
            batch_size: 批处理大小 (GPU 可适当增大)
            normalize: 是否归一化 (cosine 相似度建议开启)

        Returns:
            list[list[float]]: 对应的向量列表
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()

    def encode_single(self, text: str, normalize: bool = True) -> list[float]:
        """编码单条文本"""
        result = self.encode([text], normalize=normalize)
        return result[0]

