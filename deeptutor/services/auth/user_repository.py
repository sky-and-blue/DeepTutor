"""
用户仓库模块

提供用户相关的数据库操作
"""

from typing import Optional
from sqlalchemy import select
from .models import User, UserCreate
from .security import get_password_hash
from .database import get_async_session_factory


class UserRepository:
    """
    用户仓库类，提供用户相关的数据库操作
    """
    
    async def create_user(self, user_create: UserCreate):
        """
        创建新用户
        
        Args:
            user_create: 用户创建数据
            
        Returns:
            dict: 创建的用户响应字典
            
        Raises:
            ValueError: 当用户名或邮箱已存在时
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            try:
                # 检查用户名是否已存在
                result = await session.execute(
                    select(User).where(User.username == user_create.username)
                )
                if result.scalar_one_or_none():
                    raise ValueError(f"用户名 '{user_create.username}' 已被注册")
                
                # 检查邮箱是否已存在
                result = await session.execute(
                    select(User).where(User.email == user_create.email)
                )
                if result.scalar_one_or_none():
                    raise ValueError(f"邮箱 '{user_create.email}' 已被注册")
                
                # 创建新用户
                hashed_password = get_password_hash(user_create.password)
                new_user = User(
                    username=user_create.username,
                    email=user_create.email,
                    hashed_password=hashed_password
                )
                
                session.add(new_user)
                await session.flush()
                await session.commit()
                await session.refresh(new_user)
                
                # 构建用户响应字典，完全脱离 SQLAlchemy 对象
                user_response = {
                    "id": new_user.id,
                    "username": new_user.username,
                    "email": new_user.email,
                    "created_at": new_user.created_at
                }
                
                return user_response
            except Exception as e:
                await session.rollback()
                raise
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        根据 ID 获取用户
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[User]: 用户对象，如果不存在则返回 None
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 用户对象，如果不存在则返回 None
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            email: 邮箱
            
        Returns:
            Optional[User]: 用户对象，如果不存在则返回 None
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
    
    async def update_user(self, user: User) -> User:
        """
        更新用户信息
        
        Args:
            user: 用户对象
            
        Returns:
            User: 更新后的用户对象
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            try:
                session.add(user)
                await session.flush()
                await session.commit()
                await session.refresh(user)
                return user
            except Exception as e:
                await session.rollback()
                raise
    
    async def delete_user(self, user_id: int) -> bool:
        """
        删除用户
        
        Args:
            user_id: 用户 ID
            
        Returns:
            bool: 是否删除成功
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            try:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    await session.delete(user)
                    await session.commit()
                    return True
                return False
            except Exception as e:
                await session.rollback()
                raise
