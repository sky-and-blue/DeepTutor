"""
认证 API 路由模块
提供用户注册、登录、令牌刷新和登出功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from deeptutor.logging import get_logger
from deeptutor.services.auth.models import User, UserCreate, UserResponse
from deeptutor.services.auth.user_repository import UserRepository
from deeptutor.services.auth.security import verify_password
from deeptutor.services.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from jose import JWTError
from deeptutor.services.auth.token_store import (
    store_access_token,
    store_refresh_token,
    get_token,
    delete_token,
    delete_all_user_tokens,
)
from deeptutor.services.auth.redis_client import get_redis_client, get_key_with_prefix
from deeptutor.services.settings.interface_settings import get_ui_settings

# 初始化日志
logger = get_logger("AuthAPI")

# 创建路由
router = APIRouter()

# 初始化用户仓库
user_repository = UserRepository()

# OAuth2 密码承载令牌方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


async def get_current_user_from_state(request: Request) -> User:
    """
    从 request.state 获取当前认证用户的依赖函数（高效版本）
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 当用户未认证时抛出
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    获取当前认证用户的依赖函数（完整验证版本）
    
    Args:
        token: OAuth2 访问令牌
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 当令牌无效或用户不存在时抛出
    """
    # 验证令牌是否在 Redis 中
    token_data = await get_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 解码 JWT 令牌
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期或无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证令牌类型
    if payload.get('type') != 'access':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 转换用户 ID 为整数
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户 ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从数据库获取用户
    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate):
    """
    用户注册接口
    
    Args:
        user_create: 用户创建数据，包含用户名、邮箱和密码
        
    Returns:
        dict: 创建的用户信息（不包含密码）
        
    Raises:
        HTTPException: 当用户名或邮箱已存在时返回 400 错误
        HTTPException: 当注册功能被禁用时返回 403 错误
    """
    # 检查注册功能是否被禁用
    ui_settings = get_ui_settings()
    if not ui_settings.get("allow_registration", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="注册功能已被禁用"
        )
    
    try:
        user_data = await user_repository.create_user(user_create)
        # 确保返回的是一个完全独立的字典
        response_data = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "created_at": user_data["created_at"]
        }
        logger.info(f"用户注册成功: username={response_data['username']}")
        return response_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


class LoginRequest(BaseModel):
    """登录请求模型"""
    username_or_email: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


@router.post("/login")
async def login(login_data: LoginRequest):
    """
    用户登录接口
    
    Args:
        login_data: 登录请求数据，包含 username_or_email（用户名或邮箱）和 password
        
    Returns:
        dict: 包含 access_token、refresh_token 和 token_type 的字典
        
    Raises:
        HTTPException: 当用户不存在或密码错误时返回 401 错误
        HTTPException: 当用户账户被锁定时返回 423 错误
    """
    # 尝试通过用户名或邮箱查找用户
    user: Optional[User] = None
    
    # 先尝试用用户名查找
    user = await user_repository.get_user_by_username(login_data.username_or_email)
    
    # 如果没找到，尝试用邮箱查找
    if not user:
        user = await user_repository.get_user_by_email(login_data.username_or_email)
    
    # 验证用户存在
    if not user:
        logger.warning(f"登录失败: 用户不存在 - {login_data.username_or_email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否被锁定
    redis = get_redis_client()
    lock_key = get_key_with_prefix(f"login:lock:{user.id}")
    is_locked = await redis.exists(lock_key)
    
    if is_locked:
        logger.warning(f"登录失败: 用户被锁定 - username={user.username}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="账户已被锁定，请 30 分钟后再试",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not verify_password(login_data.password, user.hashed_password):
        # 增加登录错误次数
        error_count_key = get_key_with_prefix(f"login:error:{user.id}")
        error_count = await redis.incr(error_count_key)
        
        # 设置错误计数的过期时间为 30 分钟
        if error_count == 1:
            await redis.expire(error_count_key, 30 * 60)
        
        # 如果错误次数达到 5 次，锁定用户 30 分钟
        if error_count >= 5:
            await redis.setex(lock_key, 30 * 60, "1")
            logger.warning(f"用户被锁定: 登录错误次数过多 - username={user.username}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="账户已被锁定，请 30 分钟后再试",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.warning(f"登录失败: 密码错误 - username={user.username}, 错误次数={error_count}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 登录成功，重置错误次数
    error_count_key = get_key_with_prefix(f"login:error:{user.id}")
    await redis.delete(error_count_key)
    
    # 生成令牌
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email
    )
    refresh_token = create_refresh_token(user_id=user.id)
    
    # 存储令牌到 Redis
    await store_access_token(access_token, user.id)
    await store_refresh_token(refresh_token, user.id)
    
    logger.info(f"用户登录成功: username={user.username}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """
    刷新访问令牌接口
    
    Args:
        request: 包含 refresh_token 的请求
        
    Returns:
        dict: 包含新的 access_token 的字典
        
    Raises:
        HTTPException: 当刷新令牌无效或过期时返回 401 错误
    """
    refresh_token = request.refresh_token
    
    # 验证刷新令牌是否在 Redis 中
    token_data = await get_token(refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    # 解码刷新令牌
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已过期或无效"
        )
    
    # 验证令牌类型
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    # 获取用户信息
    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    # 生成新的访问令牌
    new_access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email
    )
    
    # 存储新的访问令牌
    await store_access_token(new_access_token, user.id)
    
    logger.info(f"刷新令牌成功: user_id={user_id}")
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息接口
    
    Args:
        current_user: 当前认证用户（通过依赖注入）
        
    Returns:
        UserResponse: 当前用户信息
    """
    logger.info(f"获取用户信息: username={current_user.username}")
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    用户登出接口
    
    Args:
        current_user: 当前认证用户（通过依赖注入）
        
    Returns:
        dict: 登出成功的消息
    """
    # 清除用户的所有令牌
    await delete_all_user_tokens(current_user.id)
    
    logger.info(f"用户登出成功: username={current_user.username}")
    
    return {
        "message": "Logged out successfully"
    }
