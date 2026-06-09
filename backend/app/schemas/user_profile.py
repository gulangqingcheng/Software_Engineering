"""
用户扩展信息（个人中心）Pydantic Schema
"""
from pydantic import BaseModel


# ── Profile 子对象（嵌套在 UserInfo 中） ──
class ProfileInfo(BaseModel):
    """用户扩展信息子对象"""
    id: int
    user_id: int
    age: int | None = None
    gender: str | None = None
    major: str | None = None
    grade: str | None = None
    university: str | None = None
    education_level: str | None = None
    degree: str | None = None
    graduation_year: str | None = None
    target_position: str | None = None
    target_city: str | None = None
    skills: str | None = None
    certificates: str | None = None
    internship_experience: str | None = None
    allow_ai_use: bool = True
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ── 完整用户信息响应（含 Profile 嵌套） ──
class UserInfoResponse(BaseModel):
    """完整用户信息响应（User 基础字段 + Profile 子对象）"""
    id: int
    username: str
    email: str | None = None
    avatar_url: str | None = None
    role: str = "user"
    created_at: str
    profile: ProfileInfo | None = None

    model_config = {"from_attributes": True}


# ── 仅 Profile 响应（ai-toggle 等使用） ──
class UserProfileResponse(BaseModel):
    """用户扩展信息响应（仅 Profile 字段）"""
    id: int
    user_id: int
    age: int | None = None
    gender: str | None = None
    major: str | None = None
    grade: str | None = None
    university: str | None = None
    education_level: str | None = None
    degree: str | None = None
    graduation_year: str | None = None
    target_position: str | None = None
    target_city: str | None = None
    skills: str | None = None
    certificates: str | None = None
    internship_experience: str | None = None
    allow_ai_use: bool = True
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ── 更新用户信息 ──
class UserProfileUpdate(BaseModel):
    """更新求职信息请求（全部可选）"""
    age: int | None = None
    gender: str | None = None
    major: str | None = None
    grade: str | None = None
    university: str | None = None
    education_level: str | None = None
    degree: str | None = None
    graduation_year: str | None = None
    target_position: str | None = None
    target_city: str | None = None
    skills: str | None = None
    certificates: str | None = None
    internship_experience: str | None = None


# ── 修改密码 ──
class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


# ── 修改用户名 ──
class UsernameChangeRequest(BaseModel):
    """修改用户名请求"""
    new_username: str


# ── 头像上传响应 ──
class AvatarUploadResponse(BaseModel):
    """头像上传响应"""
    avatar_url: str


# ── AI 使用开关 ──
class AiToggleRequest(BaseModel):
    """切换 AI 使用个人信息开关"""
    allow_ai_use: bool
