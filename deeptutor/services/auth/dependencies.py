"""
认证依赖项模块

提供 FastAPI 依赖注入用于用户认证的功能
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from deeptutor.core.errors import ValidationError
from deeptutor.logging import get_logger

from .models import UserResponse
from .jwt_utils import decode_token
from .token_store import get_token
from .user_repository import UserRepository

# 全局日志实例
_logger = get_logger("auth_dependencies")

# HTTP Bearer 认证方案
security = HTTPBearer()


def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    从 Authorization header 中提取 Bearer token
    
    Args:
        credentials: FastAPI 注入的 HTTPAuthorizationCredentials 对象
        
    Returns:
        str: 提取到的 token 字符串
        
    Raises:
        HTTPException: 当认证格式不正确时抛出 401 错误
    """
    if not credentials.scheme.lower() == "bearer":
        _logger.warning("无效的认证方案")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证方案，请使用 Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not credentials.credentials:
        _logger.warning("认证令牌为空")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌不能为空",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_token_from_header),
) -> UserResponse:
    """
    获取当前认证用户的依赖项
    
    Args:
        token: 从 header 中提取的 Bearer token
        
    Returns:
        UserResponse: 当前用户的响应模型
        
    Raises:
        HTTPException: 当认证失败时抛出 401 错误
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 验证并解码 JWT token
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            _logger.warning("令牌中缺少用户 ID")
            raise credentials_exception
    except ValidationError as e:
        _logger.warning(f"JWT 令牌验证失败: {e}")
        raise credentials_exception
    
    # 检查 token 是否在 Redis 中存在
    stored_token = await get_token(token)
    if stored_token is None:
        _logger.warning("令牌不在 Redis 存储中")
        raise credentials_exception
    
    # 验证存储的 user_id 与 JWT 中的一致
    if stored_token.get("user_id") != user_id:
        _logger.warning("令牌用户 ID 不匹配")
        raise credentials_exception
    
    # 从数据库获取用户信息
    user_repo = UserRepository()
    try:
        user_id_int = int(user_id)
    except ValueError:
        _logger.warning(f"无效的用户 ID 格式: {user_id}")
        raise credentials_exception
    
    user = await user_repo.get_user_by_id(user_id_int)
    if user is None:
        _logger.warning(f"用户不存在: {user_id_int}")
        raise credentials_exception
    
    # 返回用户响应模型（不含敏感信息）
    return UserResponse.from_user(user)


async def optional_get_current_user(
    token: Optional[str] = Depends(get_token_from_header, use_cache=False),
) -> Optional[UserResponse]:
    """
    获取当前认证用户的可选依赖项（失败时不抛异常）
    
    Args:
        token: 从 header 中提取的 Bearer token，可能为 None
        
    Returns:
        Optional[UserResponse]: 当前用户的响应模型，或 None
    """
    try:
        return await get_current_user(token)
    except HTTPException:
        return None
    except Exception as e:
        _logger.warning(f"可选认证失败: {e}")
        return None
