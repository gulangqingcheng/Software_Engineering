"""
数据库引擎和会话配置
使用 SQLAlchemy 2.0 DeclarativeBase 风格
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ── 数据库引擎 ──
# 设置 MySQL 会话时区为东八区，确保 func.now() 返回本地时间
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DEBUG,  # 开发环境打印 SQL
    pool_pre_ping=True,  # 连接健康检查
    connect_args={"init_command": "SET time_zone = '+08:00'"},
)

# ── 会话工厂 ──
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── ORM 基类 ──
class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    数据库会话依赖注入函数
    用法: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
