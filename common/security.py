"""
安全工具模块

集中处理三件事：
1. 用户密码哈希与校验（bcrypt）
2. 登录态 JWT 的签发与校验
3. 用户自带 LLM API key 的加密与解密（Fernet）

配置信息一律从 config.py 获取，禁止硬编码。
"""
import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET,
    KB_ENCRYPTION_KEY,
)

logger = logging.getLogger(__name__)

# Fernet 每次加密都会生成随机 IV，因此同一把 key 加密两次的密文不同，
# 密文里自带足够信息，config 里的原始 key 无需再单独存一份
_fernet = Fernet(KB_ENCRYPTION_KEY.encode())


# ============== 密码哈希 ==============

def _prepare_password(password: str) -> bytes:
    """
    bcrypt 只取前 72 字节，超长会被静默截断（会造成密码歧义）。
    先做一次 SHA-256 + base64 预哈希，把任意长度的密码压成固定 44 字节再交给 bcrypt。
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    """
    生成密码哈希

    Args:
        password: 明文密码

    Returns:
        可直接存入数据库的哈希字符串
    """
    return bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    校验明文密码与哈希是否匹配

    Args:
        password: 明文密码
        password_hash: 数据库中存储的哈希

    Returns:
        匹配返回 True，否则 False
    """
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare_password(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError) as e:
        # 哈希格式非法（例如历史遗留的其他算法），按校验失败处理
        logger.warning(f"密码哈希格式非法: {e}")
        return False


# ============== JWT 登录态 ==============

def create_access_token(user_id: int, username: str) -> str:
    """
    签发登录态 token

    Args:
        user_id: 用户主键
        username: 用户名

    Returns:
        JWT 字符串
    """
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解析并校验登录态 token

    Args:
        token: JWT 字符串

    Returns:
        校验通过返回 payload；过期、签名不符、格式错误等一律返回 None
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("登录态已过期")
    except jwt.InvalidTokenError as e:
        logger.warning(f"登录态无效: {e}")
    return None


# ============== LLM API key 加解密 ==============

def encrypt_api_key(api_key: str) -> str:
    """
    加密用户自带的 LLM API key

    Args:
        api_key: 明文 key

    Returns:
        可安全落库的密文字符串
    """
    return _fernet.encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted: str) -> Optional[str]:
    """
    解密用户自带的 LLM API key

    Args:
        encrypted: 数据库中的密文

    Returns:
        明文 key；若因服务器更换了 KB_ENCRYPTION_KEY 而无法解密，返回 None
    """
    if not encrypted:
        return None
    try:
        return _fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # 多半是 KB_ENCRYPTION_KEY 被换掉了，旧密文永久无法解开
        logger.error("解密 LLM API key 失败：KB_ENCRYPTION_KEY 与加密时不一致，该 key 已不可用")
        return None