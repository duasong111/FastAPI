"""
Mem0 长期记忆封装

Mem0 在架构里承担两个角色：
1. 记忆提取——用 LLM 从对话中抽出值得长期记住的事实（"用户是武汉人"、"他偏好中文回答"）
2. 记忆检索——把相关记忆注入到后续提示词里，让 AI 跨会话记住用户

模型配置沿用 BYOK 约定：
- LLM 用**用户自己的** key，与用户聊天用的是同一把，服务商不产生任何费用，
  用户的对话内容也不会经过任何第三方服务端。
- Embedding 用**服务器统一持有**的硅基流动 key（免费）。

记忆向量独立存放（MEM0_PERSIST_DIR），与知识库向量互不干扰。
"""
import logging
import threading
from typing import Any, Dict, List, Optional

from mem0 import Memory

from config import (
    DEFAULT_LLM_PROVIDER,
    LLM_PROVIDERS,
    MEM0_PERSIST_DIR,
    MEM0_TOP_K,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_EMBED_MODEL,
)

logger = logging.getLogger(__name__)

# Mem0 实例内部持有 LLM/embedding 客户端，一个用户一个实例，
# 用 LRU 缓存复用，超出上限时整体清空
_memory_cache: Dict[int, Memory] = {}
_memory_lock = threading.Lock()
_MEMORY_CACHE_MAX = 100


class MemoryUnavailableError(RuntimeError):
    """记忆功能不可用（如服务器未配置 embedding key）"""


def get_user_memory(user_id: int, provider: Optional[str], api_key: str) -> Memory:
    """
    获取某个用户的 Mem0 记忆实例

    记忆按 user_id 隔离：不同用户写入的记忆互不可见。

    Args:
        user_id: 用户主键
        provider: 聊天模型服务商（用于记忆提取的 LLM）
        api_key: 用户自己的 API key

    Returns:
        该用户的 Mem0 Memory 实例

    Raises:
        MemoryUnavailableError: 缺少 embedding key 或 LLM key
    """
    if not SILICONFLOW_API_KEY:
        raise MemoryUnavailableError("服务器未配置向量模型 key，无法启用记忆功能")
    if not api_key:
        raise MemoryUnavailableError("尚未配置大模型 API key，无法启用记忆功能")

    cached = _memory_cache.get(user_id)
    if cached is not None:
        return cached

    with _memory_lock:
        cached = _memory_cache.get(user_id)
        if cached is not None:
            return cached

        provider_name = provider or DEFAULT_LLM_PROVIDER
        provider_cfg = LLM_PROVIDERS.get(provider_name)
        if provider_cfg is None:
            raise MemoryUnavailableError(f"不支持的模型服务商: {provider_name}")

        memory = Memory.from_config({
            "llm": {
                "provider": provider_name,
                "config": {
                    "model": provider_cfg["default_model"],
                    "api_key": api_key,
                    # 记忆提取要求稳定输出，温度给到最低
                    "temperature": 0.0,
                },
            },
            "embedder": {
                # 硅基流动是 OpenAI 兼容接口，走 mem0 的 openai provider + 自定义 base_url
                "provider": "openai",
                "config": {
                    "model": SILICONFLOW_EMBED_MODEL,
                    "api_key": SILICONFLOW_API_KEY,
                    "openai_base_url": SILICONFLOW_BASE_URL,
                },
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": f"mem0_user_{user_id}",
                    "path": MEM0_PERSIST_DIR,
                },
            },
        })

        if len(_memory_cache) >= _MEMORY_CACHE_MAX:
            _memory_cache.clear()
        _memory_cache[user_id] = memory
        logger.info(f"Mem0 记忆实例已就绪: 用户 {user_id} / {provider_name}")
        return memory


def evict_user_memory(user_id: int) -> None:
    """
    从缓存中移除用户的记忆实例（改 key 或换服务商时调用）

    Args:
        user_id: 用户主键
    """
    with _memory_lock:
        memory = _memory_cache.pop(user_id, None)
    if memory is not None:
        try:
            memory.close()
        except Exception:
            pass


def remember(
    memory: Memory,
    user_id: int,
    messages: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    从对话中提取并保存长期记忆

    Args:
        memory: 该用户的 Mem0 实例
        user_id: 用户主键
        messages: 本轮对话 [{"role": "user", "content": ...}, {"role": "assistant", ...}]

    Returns:
        本次提取出的记忆条目列表（可能为空，表示没有值得记的东西）
    """
    if not messages:
        return []
    try:
        result = memory.add(messages, user_id=str(user_id))
        return result.get("results", []) if isinstance(result, dict) else []
    except Exception as e:
        # 记忆提取失败不应该让用户的问答请求整个失败，降级为"本次不记忆"
        logger.warning(f"记忆提取失败（不影响本次问答）: {e}")
        return []


def recall(memory: Memory, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    检索与当前问题相关的长期记忆

    Args:
        memory: 该用户的 Mem0 实例
        query: 当前用户提问
        top_k: 召回条数，默认取 config.MEM0_TOP_K

    Returns:
        记忆条目列表，形如 [{"memory": "...", "score": 0.8}, ...]
    """
    try:
        results = memory.search(query, top_k=top_k or MEM0_TOP_K)
        if isinstance(results, dict):
            return results.get("results", [])
        return results or []
    except Exception as e:
        # 记忆检索失败降级为"无记忆"，不影响 RAG 主流程
        logger.warning(f"记忆检索失败（按无记忆继续）: {e}")
        return []


def forget_all(memory: Memory, user_id: int) -> None:
    """
    清空某个用户的全部长期记忆

    Args:
        memory: 该用户的 Mem0 实例
        user_id: 用户主键
    """
    try:
        memory.delete_all(user_id=str(user_id))
        logger.info(f"已清空用户 {user_id} 的全部记忆")
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        raise


def forget(memory: Memory, memory_id: str) -> None:
    """
    删除单条记忆

    Args:
        memory: 该用户的 Mem0 实例
        memory_id: 记忆条目 ID
    """
    memory.delete(memory_id=memory_id)


def format_memories_for_prompt(memories: List[Dict[str, Any]]) -> str:
    """
    把记忆条目拼成提示词里的"已知信息"段落

    Args:
        memories: recall() 的返回

    Returns:
        提示词片段；无记忆时返回空字符串
    """
    lines = []
    for item in memories:
        text = item.get("memory") if isinstance(item, dict) else str(item)
        if text:
            lines.append(f"- {text}")
    if not lines:
        return ""
    return "关于这位用户的已知信息（可能过时，仅供参考）：\n" + "\n".join(lines)