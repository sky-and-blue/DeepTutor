"""
MySQL 连接管理模块

使用 SQLAlchemy 2.0 异步功能管理数据库连接和会话
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from deeptutor.config.settings import auth_settings

# SQLAlchemy 基类
Base = declarative_base()

# 全局引擎和会话工厂
_engine = None
_async_session_factory = None


def get_engine():
    """
    获取或创建异步数据库引擎
    
    Returns:
        AsyncEngine: 异步数据库引擎
    """
    global _engine
    if _engine is None:
        # 使用配置的 URL
        db_url = auth_settings.mysql.url
        
        # 如果设置了密码且 URL 中没有包含密码，则修改 URL 添加密码
        if auth_settings.mysql.password and '@' in db_url:
            # 解析 URL 并添加密码
            from sqlalchemy import make_url
            url = make_url(db_url)
            if not url.password:
                # 重建 URL 并添加密码
                db_url = f"{url.drivername}://{url.username}:{auth_settings.mysql.password}@{url.host}:{url.port}/{url.database}"
        
        _engine = create_async_engine(
            db_url,
            pool_size=auth_settings.mysql.pool_size,
            max_overflow=auth_settings.mysql.max_overflow,
            pool_pre_ping=True,
        )
    return _engine


def get_async_session_factory():
    """
    获取或创建异步会话工厂
    
    Returns:
        async_sessionmaker: 异步会话工厂
    """
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    
    Yields:
        AsyncSession: 数据库会话
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库，创建表结构
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    关闭数据库连接
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
