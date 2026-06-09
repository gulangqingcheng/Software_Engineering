"""
通用响应 Pydantic Schema
提供统一的 API 响应格式
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页记录数")

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """错误响应格式"""
    code: int = Field(description="错误状态码")
    message: str = Field(description="错误消息")
    detail: str | None = Field(default=None, description="详细错误信息")
