"""
个人中心 API 路由
提供个人信息管理、账号管理、AI 使用开关功能
"""
import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.common import APIResponse
from app.schemas.user_profile import (
    AiToggleRequest,
    AvatarUploadResponse,
    PasswordChangeRequest,
    ProfileInfo,
    UserInfoResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UsernameChangeRequest,
)
from app.api.auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/v1/profile", tags=["个人中心"])

PROFILE_EXTRA_FIELDS = [
    "education_level",
    "degree",
    "graduation_year",
    "target_position",
    "target_city",
    "skills",
    "certificates",
    "internship_experience",
]


# ── 工具函数 ──

AVATAR_DIR = os.path.join(settings.UPLOAD_DIR, "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


def get_profile_or_create(db: Session, user_id: int) -> "UserProfile":
    """获取或自动创建用户 Profile 记录"""
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def profile_payload(profile: UserProfile) -> dict:
    data = {
        "id": profile.id,
        "user_id": profile.user_id,
        "age": profile.age,
        "gender": profile.gender,
        "major": profile.major,
        "grade": profile.grade,
        "university": profile.university,
        "allow_ai_use": profile.allow_ai_use,
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }
    for field in PROFILE_EXTRA_FIELDS:
        data[field] = getattr(profile, field, None)
    return data


# ── 获取个人信息 ──

@router.get("/me", response_model=APIResponse[UserInfoResponse])
async def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户个人信息（含 User 基础信息）"""
    profile = get_profile_or_create(db, current_user.id)

    return APIResponse(
        code=0,
        message="获取成功",
        data={
            # User 基础信息
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role.value if current_user.role else "user",
            "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
            # Profile 信息（嵌套）
            "profile": profile_payload(profile),
        },
    )


# ── 更新个人信息 ──

@router.put("/me", response_model=APIResponse[UserInfoResponse])
async def update_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新个人信息（年龄/性别/专业/年级/大学）"""
    profile = get_profile_or_create(db, current_user.id)

    if data.age is not None:
        if data.age < 1 or data.age > 120:
            raise HTTPException(status_code=400, detail="年龄必须在 1-120 之间")
        profile.age = data.age

    if data.gender is not None:
        profile.gender = data.gender

    if data.major is not None:
        profile.major = data.major

    if data.grade is not None:
        profile.grade = data.grade

    if data.university is not None:
        profile.university = data.university

    for field in PROFILE_EXTRA_FIELDS:
        value = getattr(data, field, None)
        if value is not None:
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return APIResponse(
        code=0,
        message="保存成功",
        data={
            # User 基础信息
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role.value if current_user.role else "user",
            "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
            # Profile 信息（嵌套）
            "profile": profile_payload(profile),
        },
    )


# ── 修改密码 ──

@router.put("/password", response_model=APIResponse[None])
async def change_password(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改密码（需验证旧密码）"""
    # 验证旧密码
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    # 检查新密码长度
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少为 6 位")

    # 更新密码
    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    return APIResponse(code=0, message="密码修改成功，请重新登录")


# ── 修改用户名 ──

@router.put("/username")
async def change_username(
    data: UsernameChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改用户名（检查是否已被占用）"""
    new_username = data.new_username.strip()

    if len(new_username) < 3 or len(new_username) > 64:
        raise HTTPException(status_code=400, detail="用户名长度需在 3-64 位之间")

    if new_username == current_user.username:
        raise HTTPException(status_code=400, detail="新用户名与当前用户名相同")

    # 检查是否已被占用
    existing = db.query(User).filter(User.username == new_username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已被占用")

    current_user.username = new_username
    db.commit()
    db.refresh(current_user)

    # 返回完整用户信息，供前端更新 store
    profile = get_profile_or_create(db, current_user.id)
    return APIResponse(
        code=0,
        message="用户名修改成功",
        data={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role.value if current_user.role else "user",
            "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
            "profile": profile_payload(profile),
        },
    )


# ── 上传头像 ──

@router.post("/avatar", response_model=APIResponse[AvatarUploadResponse])
async def upload_avatar(
    file: UploadFile = File(..., description="头像文件（JPG/PNG/GIF/WebP，最大 5MB）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传头像（保存到 uploads/avatars/）"""
    # 验证文件类型
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，仅支持 JPG/PNG/GIF/WebP",
        )

    # 验证文件大小
    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="头像文件大小不能超过 5MB")

    # 生成文件名：{user_id}_{随机16进制}.{ext}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    random_hex = secrets.token_hex(8)
    filename = f"{current_user.id}_{random_hex}.{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)

    # 保存文件
    with open(filepath, "wb") as f:
        f.write(contents)

    # 构建可访问的 URL（前端通过 /uploads/avatars/xxx.jpg 访问）
    avatar_url = f"/uploads/avatars/{filename}"
    current_user.avatar_url = avatar_url
    db.commit()

    return APIResponse(
        code=0,
        message="头像上传成功",
        data=AvatarUploadResponse(avatar_url=avatar_url),
    )


# ── AI 使用开关 ──

@router.put("/ai-toggle")
async def toggle_ai_use(
    data: AiToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换「允许 AI 使用个人信息」开关"""
    profile = get_profile_or_create(db, current_user.id)
    profile.allow_ai_use = data.allow_ai_use
    db.commit()
    db.refresh(profile)

    return APIResponse(
        code=0,
        message=f"{'已开启' if data.allow_ai_use else '已关闭'} AI 使用个人信息",
        data=profile_payload(profile),
    )
