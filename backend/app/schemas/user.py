"""
用户相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── 注册 ──
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    email: EmailStr | None = Field(default=None, description="电子邮箱")


# ── 登录 ──
class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


# ── Token 响应 ──
class TokenResponse(BaseModel):
    """JWT Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


# ── 用户信息响应 ──
class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str | None = None
    avatar_url: str | None = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """登录响应（含 Token + 用户信息）"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class UserUpdateRequest(BaseModel):
    """更新用户信息请求"""
    email: EmailStr | None = None
    avatar_url: str | None = None
