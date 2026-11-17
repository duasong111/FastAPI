"""
大模型客户端工厂

两种模型，两种 key 来源：

1. 聊天模型（DeepSeek / MiniMax）—— BYOK，key 由用户自己上传。
   服务器不持有任何聊天模型的 key，每次调用用当前用户自己的 key 构造客户端。
   DeepSeek 与 MiniMax 都是 OpenAI 兼容协议，因此两者共用 ChatOpenAI，
   只换 base_url / model / api_key。

2. 向量模型（BAAI/bge-m3）—— 服务器统一持有一把硅基流动的 key，所有用户共用。
   DeepSeek 不提供 embedding 接口，且该模型免费，成本可忽略。

配置信息一律从 config.py 获取，禁止硬编码。
"""
import hashlib
import logging
import threading
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import (
    DEFAULT_LLM_PROVIDER,
    LLM_PROVIDERS,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_EMBED_MODEL,
)

logger = logging.getLogger(__name__)


class LLMConfigError(ValueError):
    """服务商或模型配置不合法"""


# ============== 聊天模型（BYOK）==============

# 聊天客户端缓存：同一用户连续提问时复用同一个实例，
# 避免每次请求都新建 http 连接池。
# 缓存键里只放 key 的哈希，不放明文 key，避免密钥出现在日志/内存转储里。
_chat_model_cache: Dict[tuple, ChatOpenAI] = {}
_chat_model_lock = threading.Lock()
_CHAT_MODEL_CACHE_MAX = 200


def list_providers() -> List[Dict[str, Any]]:
    """
    列出所有可选的聊天模型服务商

    Returns:
        [{"provider": "deepseek", "models": [...], "default_model": "..."}, ...]
    """
    return [
        {
            "provider": name,
            "models": cfg["models"],
            "default_model": cfg["default_model"],
        }
        for name, cfg in LLM_PROVIDERS.items()
    ]


def resolve_provider(provider: Optional[str]) -> str:
    """
    解析服务商名称，缺省回落到 config 中的默认服务商

    Args:
        provider: 服务商名称，None 或空表示用默认值

    Returns:
        合法的服务商名称

    Raises:
        LLMConfigError: 服务商不受支持
    """
    name = provider or DEFAULT_LLM_PROVIDER
    if name not in LLM_PROVIDERS:
        supported = "、".join(LLM_PROVIDERS)
        raise LLMConfigError(f"不支持的模型服务商: {name}（可选: {supported}）")
    return name


def get_chat_model(
    provider: Optional[str],
    api_key: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> ChatOpenAI:
    """
    构造聊天模型客户端（使用调用方自带的 API key）

    Args:
        provider: 服务商，如 "deepseek" / "minimax"；None 用默认值
        api_key: 用户自己的 API key
        model: 模型名；None 用该服务商的默认模型
        temperature: 采样温度

    Returns:
        LangChain 的 ChatOpenAI 实例

    Raises:
        LLMConfigError: 服务商或模型不受支持，或未提供 key
    """
    if not api_key:
        raise LLMConfigError("尚未配置大模型 API key，请先在「模型设置」中上传")

    provider_name = resolve_provider(provider)
    provider_cfg = LLM_PROVIDERS[provider_name]

    # 模型名为空时用服务商默认模型；显式传了但不在清单里直接报错，
    # 避免用户拼错模型名后拿到一个看似正常实则一直报错的请求
    model_name = model or provider_cfg["default_model"]
    if model_name not in provider_cfg["models"]:
        supported = "、".join(provider_cfg["models"])
        raise LLMConfigError(f"服务商 {provider_name} 不支持模型 {model_name}（可选: {supported}）")

    # 缓存键只含 key 的哈希，不含明文
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
    cache_key = (provider_name, key_hash, model_name, temperature)

    with _chat_model_lock:
        cached = _chat_model_cache.get(cache_key)
        if cached is not None:
            return cached

    client = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=provider_cfg["base_url"],
        temperature=temperature,
        max_retries=2,
        timeout=60,
    )

    with _chat_model_lock:
        # 缓存满了就整体清空，LRU 的收益在这个量级下不值得引入额外复杂度
        if len(_chat_model_cache) >= _CHAT_MODEL_CACHE_MAX:
            _chat_model_cache.clear()
        _chat_model_cache[cache_key] = client

    return client


# ============== 向量模型（服务器统一持有）==============

_embeddings_instance: Optional[OpenAIEmbeddings] = None
_embeddings_lock = threading.Lock()


def get_embeddings() -> OpenAIEmbeddings:
    """
    获取向量模型客户端（单例）

    向量模型由服务器统一提供，所有用户共用同一把 key，
    因此这里做成进程级单例，避免每次向量化都重建 http 连接池。

    Returns:
        LangChain 的 OpenAIEmbeddings 实例

    Raises:
        LLMConfigError: 服务器未配置向量模型 key
    """
    global _embeddings_instance

    if _embeddings_instance is not None:
        return _embeddings_instance

    with _embeddings_lock:
        if _embeddings_instance is None:
            if not SILICONFLOW_API_KEY:
                raise LLMConfigError(
                    "服务器未配置向量模型 key，请在 .env 中设置 SILICONFLOW_API_KEY"
                )
            _embeddings_instance = OpenAIEmbeddings(
                model=SILICONFLOW_EMBED_MODEL,
                api_key=SILICONFLOW_API_KEY,
                base_url=SILICONFLOW_BASE_URL,
                # bge-m3 支持 8192 长上下文，批量调大能显著减少请求次数
                chunk_size=16,
                check_embedding_ctx_length=False,
            )
    return _embeddings_instance