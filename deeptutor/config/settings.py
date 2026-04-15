"""
Configuration Settings for DeepTutor

Environment Variables:
    LLM_RETRY__MAX_RETRIES: Maximum retry attempts for LLM calls (default: 3)
    LLM_RETRY__BASE_DELAY: Base delay between retries in seconds (default: 1.0)
    LLM_RETRY__EXPONENTIAL_BACKOFF: Whether to use exponential backoff (default: True)
    
    AUTH_JWT__SECRET_KEY: JWT 签名密钥 (默认: 随机生成)
    AUTH_JWT__ALGORITHM: JWT 签名算法 (默认: HS256)
    AUTH_JWT__ACCESS_TOKEN_EXPIRE_MINUTES: 访问令牌过期时间(分钟) (默认: 30)
    AUTH_JWT__REFRESH_TOKEN_EXPIRE_DAYS: 刷新令牌过期时间(天) (默认: 7)
    
    AUTH_MYSQL__URL: MySQL 连接 URL (默认: mysql+aiomysql://root@localhost:3306/deeptutor_auth)
    AUTH_MYSQL__PASSWORD: MySQL 密码（如果在URL中未指定）
    AUTH_MYSQL__POOL_SIZE: 数据库连接池大小 (默认: 10)
    AUTH_MYSQL__MAX_OVERFLOW: 连接池最大溢出数量 (默认: 5)
    
    AUTH_REDIS__URL: Redis 连接 URL (默认: redis://localhost:6379)
    AUTH_REDIS__PREFIX: Redis 键前缀 (默认: deeptutor:)

Examples:
    export LLM_RETRY__MAX_RETRIES=5
    export LLM_RETRY__BASE_DELAY=2.0
    export LLM_RETRY__EXPONENTIAL_BACKOFF=false
    
    export AUTH_JWT__SECRET_KEY=your-secret-key
    export AUTH_JWT__ACCESS_TOKEN_EXPIRE_MINUTES=60
    export AUTH_MYSQL__URL=mysql+aiomysql://user:password@localhost:3306/my_auth_db
    export AUTH_REDIS__PREFIX=myapp:
"""

import secrets
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMRetryConfig(BaseModel):
    max_retries: int = Field(default=8, description="Maximum retry attempts for LLM calls")
    base_delay: float = Field(default=5.0, description="Base delay between retries in seconds")
    exponential_backoff: bool = Field(
        default=True, description="Whether to use exponential backoff"
    )


class JWTConfig(BaseModel):
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT 签名密钥，用于生成和验证 JWT 令牌"
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT 签名算法"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="访问令牌过期时间(分钟)"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="刷新令牌过期时间(天)"
    )


class MySQLConfig(BaseModel):
    url: str = Field(
        default="mysql+aiomysql://root@localhost:3306/deeptutor_auth",
        description="MySQL 连接 URL"
    )
    password: Optional[str] = Field(
        default=None,
        description="MySQL 密码（如果在URL中未指定）"
    )
    pool_size: int = Field(
        default=10,
        description="数据库连接池大小"
    )
    max_overflow: int = Field(
        default=5,
        description="连接池最大溢出数量"
    )


class RedisConfig(BaseModel):
    url: str = Field(
        default="redis://localhost:6379",
        description="Redis 连接 URL"
    )
    prefix: str = Field(
        default="deeptutor:",
        description="Redis 键前缀"
    )


class AuthConfig(BaseModel):
    jwt: JWTConfig = Field(default_factory=JWTConfig, description="JWT 认证配置")
    mysql: MySQLConfig = Field(default_factory=MySQLConfig, description="MySQL 数据库配置")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis 缓存配置")


class LLMSettings(BaseSettings):
    # LLM retry configuration
    retry: LLMRetryConfig = Field(default_factory=LLMRetryConfig)

    # Deprecated: use retry instead
    @property
    def llm_retry(self):
        import warnings

        warnings.warn(
            "settings.llm_retry is deprecated, use settings.retry instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.retry

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_nested_delimiter="__",
    )


class AuthSettings(BaseSettings):
    # 认证配置
    jwt: JWTConfig = Field(default_factory=JWTConfig, description="JWT 认证配置")
    mysql: MySQLConfig = Field(default_factory=MySQLConfig, description="MySQL 数据库配置")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis 缓存配置")

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_nested_delimiter="__",
    )


class Settings:
    # LLM 配置
    llm: LLMSettings = Field(default_factory=LLMSettings)
    
    # 认证配置
    auth: AuthSettings = Field(default_factory=AuthSettings)


# Global settings instances
llm_settings = LLMSettings()
auth_settings = AuthSettings()

# 保持向后兼容
settings = llm_settings
