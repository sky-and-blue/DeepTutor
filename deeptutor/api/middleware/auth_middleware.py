"""
认证中间件模块

提供统一的 API 认证中间件
"""

from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from deeptutor.logging import get_logger
from deeptutor.services.auth import (
    get_token_from_header,
    decode_token,
    get_token,
    get_user_by_id,
)

# 配置日志
logger = get_logger("AuthMiddleware")

# 不需要认证的路径
# 只允许必要的公共路径，避免通配符匹配
_PUBLIC_PATHS = [
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/system/status",
    "/api/v1/system/runtime-topology",
    "/api/outputs",
]


def is_public_path(path: str) -> bool:
    """
    检查路径是否为公共路径
    
    Args:
        path: 请求路径
        
    Returns:
        bool: 是否为公共路径
    """
    for public_path in _PUBLIC_PATHS:
        if public_path.endswith("*"):
            # 前缀匹配
            prefix = public_path[:-1]
            if path.startswith(prefix):
                return True
        else:
            # 精确匹配
            if path == public_path:
                return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件类
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求的认证逻辑
        
        Args:
            request: 请求对象
            call_next: 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        # 检查是否为公共路径
        path = request.url.path
        
        # 跳过 WebSocket 请求（需要在 WebSocket 连接时单独处理认证）
        if request.scope.get("type") == "websocket":
            return await call_next(request)
        
        # 只对 API 路径进行认证检查，跳过其他路径（如前端页面）
        # 并且只对非公共 API 路径进行认证
        if path.startswith("/api/") and not is_public_path(path):
            # 获取令牌
            try:
                token = get_token_from_header(request)
            except HTTPException:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "未提供认证令牌"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 验证令牌
            try:
                # 检查令牌是否在 Redis 中
                token_data = await get_token(token)
                if not token_data:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "无效的认证令牌"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # 解码令牌
                payload = decode_token(token)
                
                # 获取用户 ID
                user_id_str = payload.get("sub")
                if not user_id_str:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "无效的认证令牌"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # 转换用户 ID 为整数
                try:
                    user_id = int(user_id_str)
                except ValueError:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "无效的用户 ID"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # 获取用户信息
                user = await get_user_by_id(user_id)
                if not user:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "用户不存在"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # 将用户信息存储到请求状态中
                request.state.user = user
                
            except Exception as e:
                logger.error(f"认证失败: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "认证失败"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        

        
        # 继续处理请求
        response = await call_next(request)
        return response
