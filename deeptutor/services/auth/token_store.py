"""
令牌存储和管理模块

提供访问令牌和刷新令牌的存储、获取、删除功能
"""

import json
from typing import Optional, Dict, Any
from datetime import timedelta

from deeptutor.config.settings import auth_settings
from deeptutor.logging import get_logger
from deeptutor.services.auth.redis_client import get_redis_client, get_key_with_prefix

# 全局日志实例
_logger = get_logger("TokenStore")

# 令牌类型常量
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _get_token_key(token_type: str, token: str) -> str:
    """
    生成令牌存储的键名
    
    Args:
        token_type: 令牌类型 (access/refresh)
        token: 令牌值
        
    Returns:
        str: Redis 键名
    """
    return get_key_with_prefix(f"token:{token_type}:{token}")


def _get_user_tokens_key(user_id: str, token_type: str) -> str:
    """
    生成用户令牌列表的键名
    
    Args:
        user_id: 用户 ID
        token_type: 令牌类型 (access/refresh)
        
    Returns:
        str: Redis 键名
    """
    return get_key_with_prefix(f"user_tokens:{user_id}:{token_type}")


async def store_access_token(
    token: str,
    user_id: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    存储访问令牌
    
    Args:
        token: 访问令牌
        user_id: 用户 ID
        extra_data: 额外的令牌数据
    """
    redis = get_redis_client()
    token_key = _get_token_key(TOKEN_TYPE_ACCESS, token)
    user_tokens_key = _get_user_tokens_key(user_id, TOKEN_TYPE_ACCESS)
    
    # 构建令牌数据
    token_data = {
        "user_id": user_id,
        "type": TOKEN_TYPE_ACCESS,
        "extra": extra_data or {},
    }
    
    # 设置过期时间
    expire_seconds = auth_settings.jwt.access_token_expire_minutes * 60
    
    try:
        # 存储令牌数据
        await redis.setex(
            token_key,
            expire_seconds,
            json.dumps(token_data),
        )
        
        # 将令牌添加到用户的令牌列表中
        await redis.sadd(user_tokens_key, token)
        # 设置用户令牌列表的过期时间（比令牌过期时间长一点，以便清理）
        await redis.expire(user_tokens_key, expire_seconds + 300)
        
        _logger.debug(f"存储访问令牌: user_id={user_id}")
    except Exception as e:
        _logger.error(f"存储访问令牌失败: {e}")
        raise


async def store_refresh_token(
    token: str,
    user_id: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    存储刷新令牌
    
    Args:
        token: 刷新令牌
        user_id: 用户 ID
        extra_data: 额外的令牌数据
    """
    redis = get_redis_client()
    token_key = _get_token_key(TOKEN_TYPE_REFRESH, token)
    user_tokens_key = _get_user_tokens_key(user_id, TOKEN_TYPE_REFRESH)
    
    # 构建令牌数据
    token_data = {
        "user_id": user_id,
        "type": TOKEN_TYPE_REFRESH,
        "extra": extra_data or {},
    }
    
    # 设置过期时间
    expire_seconds = auth_settings.jwt.refresh_token_expire_days * 24 * 60 * 60
    
    try:
        # 存储令牌数据
        await redis.setex(
            token_key,
            expire_seconds,
            json.dumps(token_data),
        )
        
        # 将令牌添加到用户的令牌列表中
        await redis.sadd(user_tokens_key, token)
        # 设置用户令牌列表的过期时间（比令牌过期时间长一点，以便清理）
        await redis.expire(user_tokens_key, expire_seconds + 300)
        
        _logger.debug(f"存储刷新令牌: user_id={user_id}")
    except Exception as e:
        _logger.error(f"存储刷新令牌失败: {e}")
        raise


async def get_token(token: str) -> Optional[Dict[str, Any]]:
    """
    获取令牌数据
    
    Args:
        token: 令牌值
        
    Returns:
        Optional[Dict[str, Any]]: 令牌数据，如果不存在返回 None
    """
    redis = get_redis_client()
    
    # 先尝试作为访问令牌获取
    token_key = _get_token_key(TOKEN_TYPE_ACCESS, token)
    data = await redis.get(token_key)
    
    if data is None:
        # 再尝试作为刷新令牌获取
        token_key = _get_token_key(TOKEN_TYPE_REFRESH, token)
        data = await redis.get(token_key)
    
    if data is not None:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            _logger.error(f"令牌数据解析失败: {token}")
            return None
    
    return None


async def delete_token(token: str) -> bool:
    """
    删除令牌
    
    Args:
        token: 令牌值
        
    Returns:
        bool: 是否成功删除
    """
    redis = get_redis_client()
    
    # 获取令牌数据以获取 user_id
    token_data = await get_token(token)
    if token_data is None:
        return False
    
    user_id = token_data["user_id"]
    token_type = token_data["type"]
    
    try:
        # 删除令牌数据
        token_key = _get_token_key(token_type, token)
        await redis.delete(token_key)
        
        # 从用户的令牌列表中移除
        user_tokens_key = _get_user_tokens_key(user_id, token_type)
        await redis.srem(user_tokens_key, token)
        
        _logger.debug(f"删除令牌: user_id={user_id}, type={token_type}")
        return True
    except Exception as e:
        _logger.error(f"删除令牌失败: {e}")
        return False


async def delete_all_user_tokens(user_id: str) -> None:
    """
    删除用户的所有令牌
    
    Args:
        user_id: 用户 ID
    """
    redis = get_redis_client()
    
    for token_type in [TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH]:
        user_tokens_key = _get_user_tokens_key(user_id, token_type)
        
        try:
            # 获取用户所有令牌
            tokens = await redis.smembers(user_tokens_key)
            
            # 删除每个令牌
            for token in tokens:
                token_key = _get_token_key(token_type, token)
                await redis.delete(token_key)
            
            # 删除用户令牌列表
            await redis.delete(user_tokens_key)
            
            _logger.debug(f"删除用户所有 {token_type} 令牌: user_id={user_id}")
        except Exception as e:
            _logger.error(f"删除用户令牌失败: user_id={user_id}, error={e}")
