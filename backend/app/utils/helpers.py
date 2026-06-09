"""
通用工具函数模块
包含 JWT 生成、文件处理、数据验证等辅助函数
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings


def generate_unique_filename(original_filename: str) -> str:
    """
    生成唯一文件名（UUID + 原始扩展名）
    
    Args:
        original_filename: 原始文件名
        
    Returns:
        str: 唯一标识的文件名
    """
    ext = os.path.splitext(original_filename)[1]
    return f"{uuid.uuid4().hex}{ext}"


def ensure_directory(path: str) -> str:
    """
    确保目录存在，不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        str: 目录路径
    """
    os.makedirs(path, exist_ok=True)
    return path


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（小写）
    
    Args:
        filename: 文件名
        
    Returns:
        str: 小写扩展名（不含点号）
    """
    return os.path.splitext(filename)[1].lower().lstrip(".")


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为可读形式
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小（如 "2.5 MB"）
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def validate_file_type(filename: str, allowed_types: list[str]) -> bool:
    """
    验证文件类型是否在允许列表中
    
    Args:
        filename: 文件名
        allowed_types: 允许的扩展名列表（如 ["pdf", "docx"]）
        
    Returns:
        bool: 是否允许
    """
    ext = get_file_extension(filename)
    return ext in allowed_types


def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 安全文件名
    """
    import re
    # 保留中文、英文、数字、下划线、连字符和点号
    safe = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', filename)
    return safe.strip()


def get_current_beijing_time() -> datetime:
    """
    获取当前北京时间（UTC+8）
    
    Returns:
        datetime: 北京时间
    """
    return datetime.now(timezone.utc) + timedelta(hours=8)
