"""
Redis 连接管理模块

提供异步 Redis 连接池、客户端的获取和关闭方法
"""

from typing import Optional
from redis.asyncio import Redis, ConnectionPool

from deeptutor.config.settings import auth_settings
from deeptutor.logging import get_logger

# 全局日志实例
_logger = get_logger("RedisClient")

# 全局 Redis 连接池和客户端实例
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


def get_redis_pool() -> ConnectionPool:
    """
    获取或创建 Redis 连接池实例
    
    Returns:
        ConnectionPool: Redis 连接池
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            auth_settings.redis.url,
            max_connections=50,  # 最大连接数
            decode_responses=True,  # 自动解码响应为字符串
        )
        _logger.info(f"初始化 Redis 连接池: {auth_settings.redis.url}")
    return _redis_pool


def get_redis_client() -> Redis:
    """
    获取或创建 Redis 客户端实例
    
    Returns:
        Redis: Redis 异步客户端
    """
    global _redis_client
    if _redis_client is None:
        pool = get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
        _logger.info("初始化 Redis 客户端")
    return _redis_client


def get_key_with_prefix(key: str) -> str:
    """
    为键添加前缀
    
    Args:
        key: 原始键名
        
    Returns:
        str: 添加前缀后的键名
    """
    return f"{auth_settings.redis.prefix}{key}"


async def close_redis_client() -> None:
    """
    关闭 Redis 客户端和连接池
    
    在应用退出时调用，释放资源
    """
    global _redis_client, _redis_pool
    
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        _logger.info("已关闭 Redis 客户端")
    
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
        _logger.info("已关闭 Redis 连接池")
