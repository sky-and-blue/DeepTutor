"""
JWT 工具模块

提供 JWT 令牌的生成和验证功能
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt

from deeptutor.config.settings import auth_settings


def create_access_token(user_id: int, username: str, email: str) -> str:
    """
    创建访问令牌
    
    Args:
        user_id: 用户 ID
        username: 用户名
        email: 邮箱
        
    Returns:
        str: JWT 访问令牌
    """
    # 过期时间
    expire = datetime.utcnow() + timedelta(minutes=auth_settings.jwt.access_token_expire_minutes)
    
    # 令牌数据
    to_encode = {
        "sub": str(user_id),  # 转换为字符串
        "username": username,
        "email": email,
        "type": "access",
        "exp": expire
    }
    
    # 生成令牌
    encoded_jwt = jwt.encode(
        to_encode,
        auth_settings.jwt.secret_key,
        algorithm=auth_settings.jwt.algorithm
    )
    
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    """
    创建刷新令牌
    
    Args:
        user_id: 用户 ID
        
    Returns:
        str: JWT 刷新令牌
    """
    # 过期时间
    expire = datetime.utcnow() + timedelta(days=auth_settings.jwt.refresh_token_expire_days)
    
    # 令牌数据
    to_encode = {
        "sub": str(user_id),  # 转换为字符串
        "type": "refresh",
        "exp": expire
    }
    
    # 生成令牌
    encoded_jwt = jwt.encode(
        to_encode,
        auth_settings.jwt.secret_key,
        algorithm=auth_settings.jwt.algorithm
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    解码和验证 JWT 令牌
    
    Args:
        token: JWT 令牌
        
    Returns:
        Dict[str, Any]: 令牌载荷
        
    Raises:
        JWTError: 当令牌无效时
    """
    payload = jwt.decode(
        token,
        auth_settings.jwt.secret_key,
        algorithms=[auth_settings.jwt.algorithm]
    )
    return payload
