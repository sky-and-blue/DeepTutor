"""
用户模型模块

定义用户相关的数据模型
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from datetime import datetime
from pydantic import BaseModel, EmailStr

from .database import Base


class User(Base):
    """
    用户模型
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserCreate(BaseModel):
    """
    用户创建模型
    """
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """
    用户响应模型
    """
    id: int
    username: str
    email: str
    created_at: datetime
    
    @classmethod
    def from_user(cls, user: User):
        """
        从 User 对象创建 UserResponse
        
        Args:
            user: User 对象
            
        Returns:
            UserResponse: 用户响应对象
        """
        # 提取所有属性值到普通变量，完全脱离 SQLAlchemy 对象
        id = user.id
        username = user.username
        email = user.email
        created_at = user.created_at
        
        # 使用普通变量构建响应对象
        return cls(
            id=id,
            username=username,
            email=email,
            created_at=created_at
        )
