"""
认证接口路由
提供用户注册、登录、Token 刷新等功能
使用 JWT (python-jose) + passlib (bcrypt) 实现
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse, ErrorResponse
from app.schemas.user import (
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# ── 密码加密上下文 ──
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── JWT 安全方案 ──
security = HTTPBearer()


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配"""
    # bcrypt 最大支持 72 字节，超出部分会被截断
    # 为保持一致性，显式截断
    password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(password_bytes.decode('utf-8', errors='ignore'), hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT 访问令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """生成 JWT 刷新令牌（有效期更长）"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """解码并验证 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前登录用户（依赖注入）"""
    payload = decode_token(credentials.credentials)

    # 验证 token 类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户标识",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    return user


# ── 路由端点 ──


@router.post("/register", response_model=APIResponse[UserResponse])
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册",
        )

    # 检查邮箱是否已存在
    if request.email:
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册",
            )

    # 创建用户
    user = User(
        username=request.username,
        password_hash=hash_password(request.password),
        email=request.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return APIResponse(data=UserResponse.model_validate(user), message="注册成功")


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    # 查找用户
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 生成 Token
    token_data = {"sub": str(user.id), "username": user.username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return APIResponse(
        data=LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        ),
        message="登录成功",
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """刷新访问令牌"""
    payload = decode_token(request.refresh_token)

    # 验证 token 类型
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户标识",
        )

    # 验证用户是否存在
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 生成新的 Token 对
    token_data = {"sub": str(user.id), "username": user.username}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return APIResponse(
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        ),
        message="Token 刷新成功",
    )


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return APIResponse(data=UserResponse.model_validate(current_user))
