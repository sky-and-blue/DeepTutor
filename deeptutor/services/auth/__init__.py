"""
DeepTutor 认证服务模块

包含用户管理、数据库连接、密码安全等功能
"""

from .database import (
    Base,
    get_engine,
    get_async_session_factory,
    get_db,
    init_db,
    close_db,
)
from .models import (
    User,
    UserCreate,
    UserResponse,
)
from .user_repository import UserRepository
from .security import (
    verify_password,
    get_password_hash,
)
from .jwt_utils import (
    decode_token,
    create_access_token,
    create_refresh_token,
)
from .token_store import (
    get_token,
    store_access_token,
    store_refresh_token,
    delete_token,
    delete_all_user_tokens,
)
from .dependencies import (
    get_token_from_header,
    get_current_user,
    optional_get_current_user,
)

# 创建 UserRepository 实例
user_repository = UserRepository()

# 封装 UserRepository 方法为独立函数
async def get_user_by_id(user_id: int):
    """根据 ID 获取用户"""
    return await user_repository.get_user_by_id(user_id)

async def get_user_by_username(username: str):
    """根据用户名获取用户"""
    return await user_repository.get_user_by_username(username)

async def get_user_by_email(email: str):
    """根据邮箱获取用户"""
    return await user_repository.get_user_by_email(email)

__all__ = [
    "Base",
    "get_engine",
    "get_async_session_factory",
    "get_db",
    "init_db",
    "close_db",
    "User",
    "UserCreate",
    "UserResponse",
    "UserRepository",
    "user_repository",
    "get_user_by_id",
    "get_user_by_username",
    "get_user_by_email",
    "verify_password",
    "get_password_hash",
    "decode_token",
    "create_access_token",
    "create_refresh_token",
    "get_token",
    "store_access_token",
    "store_refresh_token",
    "delete_token",
    "delete_all_user_tokens",
    "get_token_from_header",
    "get_current_user",
    "optional_get_current_user",
]
