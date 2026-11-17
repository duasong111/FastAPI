"""
长期记忆功能模块

把 Mem0 包装成业务接口：列出/检索/删除用户的记忆。

Mem0 实例本身在 common/memory.py 里管理（按用户缓存），
本模块负责取实例、转换 Mem0 的原始返回结构。
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

import common.memory as memory_mod
from common.memory import MemoryUnavailableError
from databases.models import User
from functions.User import AuthError, get_user_by_id

logger = logging.getLogger(__name__)


def get_memory_for_user(db: Session, user_id: int):
    """
    取当前用户的 Mem0 实例

    记忆提取用的是用户自己的 key，与聊天同一个服务商，
    因此这里必须先确认用户已配置模型。

    Args:
        db: 数据库会话
        user_id: 用户主键

    Returns:
        该用户的 Mem0 Memory 实例

    Raises:
        AuthError: 用户未配置大模型 key
        MemoryUnavailableError: 记忆功能不可用
    """
    import common.security as security

    user = get_user_by_id(db, user_id)
    if not user.has_llm_key:
        raise AuthError(
            "尚未配置大模型 API key，请先调用 PUT /api/auth/llm-config 上传",
            status_code=400,
        )

    api_key = security.decrypt_api_key(user.llm_api_key_encrypted)
    if not api_key:
        raise AuthError("保存的 API key 已无法解密，请重新上传", status_code=400)

    return memory_mod.get_user_memory(user_id, user.llm_provider, api_key)


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    把 Mem0 的单条返回转成统一结构

    Mem0 各版本/各 provider 的返回字段名不完全一致，这里做一层兜底。

    Args:
        raw: Mem0 原始返回项

    Returns:
        {"memory_id", "content", "score", "created_at"}
    """
    created_at = raw.get("created_at") or raw.get("updated_at")
    if hasattr(created_at, "strftime"):
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
    elif created_at is not None:
        created_at = str(created_at)

    return {
        "memory_id": raw.get("id") or raw.get("memory_id"),
        "content": raw.get("memory") or raw.get("text") or "",
        "score": raw.get("score"),
        "created_at": created_at,
    }


def list_memories(
    db: Session,
    user_id: int,
    query: Optional[str] = None,
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    列出或检索用户的长期记忆

    Args:
        db: 数据库会话
        user_id: 用户主键
        query: 检索关键词；为 None 时列出全部记忆
        top_k: 召回条数

    Returns:
        [{"memory_id", "content", "score", "created_at"}, ...]

    Raises:
        AuthError: 用户未配置大模型 key
        MemoryUnavailableError: 记忆功能不可用
    """
    memory = get_memory_for_user(db, user_id)

    if query:
        raw_items = memory_mod.recall(memory, query, top_k=top_k)
    else:
        try:
            result = memory.get_all(user_id=str(user_id), top_k=top_k)
            raw_items = result.get("results", []) if isinstance(result, dict) else (result or [])
        except Exception as e:
            logger.warning(f"列出记忆失败（按空列表返回）: {e}")
            raw_items = []

    return [_normalize(item) for item in raw_items if isinstance(item, dict)]


def delete_memory(db: Session, user_id: int, memory_id: str) -> int:
    """
    删除单条记忆

    Args:
        db: 数据库会话
        user_id: 用户主键
        memory_id: 记忆条目 ID

    Returns:
        本次删除的条数

    Raises:
        AuthError: 用户未配置大模型 key
        MemoryUnavailableError: 记忆功能不可用
    """
    memory = get_memory_for_user(db, user_id)
    memory_mod.forget(memory, memory_id)
    return 1


def clear_all_memories(db: Session, user_id: int) -> int:
    """
    清空用户的全部记忆

    Args:
        db: 数据库会话
        user_id: 用户主键

    Returns:
        清空前统计到的条数

    Raises:
        AuthError: 用户未配置大模型 key
        MemoryUnavailableError: 记忆功能不可用
    """
    memory = get_memory_for_user(db, user_id)
    memory_mod.forget_all(memory, user_id)
    return 0