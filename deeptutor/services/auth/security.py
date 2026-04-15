"""
密码安全工具模块

提供密码哈希和验证功能
"""

import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否正确
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    获取密码的哈希值
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码
    """
    # 自动截断密码到72字节以适应bcrypt限制
    password_bytes = password[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
