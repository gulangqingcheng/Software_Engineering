"""
应用配置管理模块
使用 pydantic-settings 从 .env 文件和环境变量中读取配置
"""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 应用基础配置 ──
    APP_NAME: str = "传智杯-AIGC面试助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ── 数据库配置 ──
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/chuanzhibei?charset=utf8mb4"
    # 为异步预留（如果需要）
    DATABASE_URL_ASYNC: str = "mysql+aiomysql://root:password@localhost:3306/chuanzhibei?charset=utf8mb4"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # ── Redis 配置 ──
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_CACHE_TTL: int = 3600  # 默认缓存过期时间（秒）

    # ── LLM API 配置（DeepSeek） ──
    LLM_API_KEY: str = "your-api-key-here"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL_NAME: str = "deepseek-v4-flash"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 120  # LLM 请求超时（秒），DeepSeek 思考模式耗时较长

    # ── DeepSeek 思考模式配置 ──
    LLM_THINKING_ENABLED: bool = True
    LLM_REASONING_EFFORT: str = "high"  # high | max

    # ── DashScope / 阿里云配置（简历评估 + 语音识别） ──
    DASHSCOPE_API_KEY: str = ""
    QWEN_VL_MODEL: str = "qwen3-vl-flash"
    QWEN_VL_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_VL_MAX_TOKENS: int = 8192
    PARAFOUNDER_MODEL: str = "paraformer-v2"

    # ── Tavily 搜索 API 配置（面试题生成） ──
    TAVILY_API_KEY: str = ""

    # ── Embedding 模型配置 ──
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DEVICE: str = "auto"  # auto | cpu | cuda（auto 自动检测 GPU）
    EMBEDDING_DIMENSION: int = 1024  # bge-large-zh 输出维度

    # ── JWT 认证配置 ──
    SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 文件上传配置 ──
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_AUDIO_TYPES: list[str] = ["audio/wav", "audio/mp3", "audio/m4a", "audio/webm"]
    ALLOWED_RESUME_TYPES: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/msword",  # .doc
    ]

    # ── ChromaDB 向量库配置 ──
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "chroma_db")
    CHROMA_COLLECTION_NAME: str = "interview_knowledge"
    CHROMA_SIMILARITY_THRESHOLD: float = 0.7

    # ── 面试题生成配置 ──
    MAX_QUESTIONS_PER_REQUEST: int = 10
    DEFAULT_QUESTIONS_COUNT: int = 5

    # ── 违禁词配置 ──
    VIOLATION_WORDS_FILE: str = str(BASE_DIR / "app" / "data" / "violation_words.txt")

    # ── CORS 配置 ──
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
