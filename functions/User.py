"""
用户功能模块

注册、登录、模型配置（BYOK）与登录态校验。

按分层规范，本模块只做业务编排：
- 数据库会话由路由层注入（db: Session）
- 密码哈希 / JWT / 密钥加解密交给 common/security.py
- 大模型客户端交给 common/llm.py
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

import common.security as security
from common.llm import LLMConfigError, get_chat_model, list_providers, resolve_provider
from databases.models import User

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """认证/授权失败"""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UserConflictError(Exception):
    """用户名已存在"""

    def __init__(self, message: str = "该用户名已被注册"):
        super().__init__(message)
        self.message = message


def build_user_data(user: User) -> Dict[str, Any]:
    """
    把 ORM 对象转成响应用的字典

    API key 明文永不出现在响应里，只回显「是否已配置」。

    Args:
        user: 用户 ORM 对象

    Returns:
        用户信息字典
    """
    return {
        "user_id": user.id,
        "username": user.username,
        "llm_provider": user.llm_provider,
        "llm_model": user.llm_model,
        "has_llm_key": user.has_llm_key,
        "providers": list_providers(),
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def register_user(db: Session, username: str, password: str) -> User:
    """
    注册新用户

    Args:
        db: 数据库会话
        username: 用户名
        password: 明文密码

    Returns:
        新建的用户 ORM 对象

    Raises:
        UserConflictError: 用户名已被占用
    """
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise UserConflictError()

    user = User(
        username=username,
        # 只存哈希，明文密码不落库、不入日志
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"新用户注册: id={user.id}, username={username}")
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    """
    校验用户名密码

    Args:
        db: 数据库会话
        username: 用户名
        password: 明文密码

    Returns:
        通过校验的用户 ORM 对象

    Raises:
        AuthError: 用户名或密码错误
    """
    user = db.query(User).filter(User.username == username).first()

    # 用户不存在时也执行一次哈希校验，避免通过响应耗时区分「用户不存在」和「密码错误」
    if user is None:
        security.verify_password(password, security.hash_password("dummy-for-timing"))
        raise AuthError("用户名或密码错误")

    if not security.verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")

    return user


def login_user(db: Session, username: str, password: str) -> Dict[str, Any]:
    """
    用户登录，签发登录态

    Args:
        db: 数据库会话
        username: 用户名
        password: 明文密码

    Returns:
        含 access_token 的登录结果字典
    """
    from config import JWT_EXPIRE_MINUTES

    user = authenticate(db, username, password)
    token = security.create_access_token(user.id, user.username)

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": JWT_EXPIRE_MINUTES * 60,
        "user": build_user_data(user),
    }


def get_user_by_id(db: Session, user_id: int) -> User:
    """
    按主键查询用户

    Args:
        db: 数据库会话
        user_id: 用户主键

    Returns:
        用户 ORM 对象

    Raises:
        AuthError: 用户不存在
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AuthError("用户不存在", status_code=401)
    return user


def resolve_user_from_token(db: Session, token: str) -> User:
    """
    用登录态令牌换取当前用户

    Header 的解析（Bearer 前缀等）属于 Web 层，放在 main.py 的依赖里，
    本函数只负责「令牌 → 用户」这一步业务判断。

    Args:
        db: 数据库会话
        token: JWT 字符串

    Returns:
        当前登录用户

    Raises:
        AuthError: 令牌无效、已过期，或令牌指向的用户已不存在
    """
    payload = security.decode_access_token(token)
    if not payload:
        raise AuthError("登录态无效或已过期，请重新登录", status_code=401)

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise AuthError("登录态格式错误", status_code=401)

    return get_user_by_id(db, user_id)


def update_llm_config(
    db: Session,
    user_id: int,
    provider: str,
    api_key: str,
    model: Optional[str] = None,
) -> User:
    """
    保存用户自带的大模型配置（BYOK）

    API key 用服务器端密钥加密后落库，服务器不保留明文。

    Args:
        db: 数据库会话
        user_id: 用户主键
        provider: 服务商标识
        api_key: 用户自己的 API key
        model: 模型名，留空用服务商默认模型

    Returns:
        更新后的用户 ORM 对象

    Raises:
        LLMConfigError: 服务商或模型不受支持
    """
    user = get_user_by_id(db, user_id)

    provider_name = resolve_provider(provider)
    provider_cfg_models = next(
        p for p in list_providers() if p["provider"] == provider_name
    )
    model_name = model or provider_cfg_models["default_model"]
    if model_name not in provider_cfg_models["models"]:
        supported = "、".join(provider_cfg_models["models"])
        raise LLMConfigError(f"服务商 {provider_name} 不支持模型 {model_name}（可选: {supported}）")

    # 服务商或 key 变了，之前缓存的 Mem0 实例绑的是旧 LLM，必须失效
    from common.memory import evict_user_memory

    evict_user_memory(user_id)

    user.llm_provider = provider_name
    user.llm_api_key_encrypted = security.encrypt_api_key(api_key)
    user.llm_model = model_name
    db.commit()
    db.refresh(user)

    logger.info(f"用户 {user_id} 更新模型配置: {provider_name} / {model_name}")
    return user


def get_user_chat_model(db: Session, user_id: int):
    """
    取出当前用户可用的聊天模型客户端

    Args:
        db: 数据库会话
        user_id: 用户主键

    Returns:
        LangChain 聊天模型实例，使用该用户自己的 key

    Raises:
        AuthError: 用户未配置可用的 API key
        LLMConfigError: 服务商或模型配置不合法
    """
    user = get_user_by_id(db, user_id)

    if not user.has_llm_key:
        raise AuthError(
            "尚未配置大模型 API key，请先调用 PUT /api/auth/llm-config 上传",
            status_code=400,
        )

    api_key = security.decrypt_api_key(user.llm_api_key_encrypted)
    if not api_key:
        raise AuthError(
            "保存的 API key 已无法解密（服务器更换了 KB_ENCRYPTION_KEY），请重新上传",
            status_code=400,
        )

    return get_chat_model(user.llm_provider, api_key, user.llm_model)