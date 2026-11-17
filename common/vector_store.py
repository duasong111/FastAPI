"""
向量库工具模块

ChromaDB 持久化客户端，按用户做物理隔离：
每个用户一个 collection（kb_user_{id}），用户的向量数据互不可见。

配置信息从 config.py 获取。
"""
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from langchain_chroma import Chroma

from config import CHROMA_COLLECTION_PREFIX, CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

# 显式声明距离度量为余弦。
# Chroma 的 similarity_search_with_score 返回的是"距离"而非相似度（越小越相似），
# 不显式指定 space 就依赖 Chroma 的默认值，换版本时行为可能变化。
_COLLECTION_METADATA = {"hnsw:space": "cosine"}

# 每个用户的 collection 句柄缓存，避免每次请求都重建 Chroma 包装对象
_user_stores: Dict[int, Chroma] = {}
_store_lock = threading.Lock()


def _get_embedding_function():
    """
    延迟引入向量模型，避免本模块在未配置 key 时导入即报错
    """
    from common.llm import get_embeddings

    return get_embeddings()


def get_collection_name(user_id: int) -> str:
    """
    生成用户专属的 collection 名

    Args:
        user_id: 用户主键

    Returns:
        collection 名称，如 "kb_user_1"
    """
    return f"{CHROMA_COLLECTION_PREFIX}{user_id}"


def get_user_store(user_id: int) -> Chroma:
    """
    获取某个用户的知识库 collection 句柄

    物理隔离：不同用户的向量落在不同 collection，检索时不可能串数据。

    Args:
        user_id: 用户主键

    Returns:
        Chroma 实例，collection 为该用户专属

    Raises:
        LLMConfigError: 服务器未配置向量模型 key
    """
    cached = _user_stores.get(user_id)
    if cached is not None:
        return cached

    with _store_lock:
        cached = _user_stores.get(user_id)
        if cached is not None:
            return cached

        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        store = Chroma(
            collection_name=get_collection_name(user_id),
            embedding_function=_get_embedding_function(),
            persist_directory=CHROMA_PERSIST_DIR,
            collection_metadata=_COLLECTION_METADATA,
        )
        _user_stores[user_id] = store
        logger.info(f"Chroma 向量库已就绪: {CHROMA_PERSIST_DIR} / {get_collection_name(user_id)}")
        return store


def add_documents(user_id: int, documents: List[Any]) -> List[str]:
    """
    向用户的知识库写入切片

    Args:
        user_id: 用户主键
        documents: LangChain Document 列表，metadata 里必须带 document_id

    Returns:
        写入的向量 id 列表
    """
    return get_user_store(user_id).add_documents(documents)


def search_documents(
    user_id: int,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> List[Tuple[Any, float]]:
    """
    在用户的知识库中做向量检索

    Args:
        user_id: 用户主键
        query: 查询文本
        top_k: 召回数量
        score_threshold: 相似度下限，低于该值的片段直接丢弃。
                         余弦距离转相似度: similarity = 1 - distance

    Returns:
        [(Document, similarity), ...]，按相似度从高到低
    """
    results = get_user_store(user_id).similarity_search_with_score(query, k=top_k)
    scored = [(doc, 1.0 - float(distance)) for doc, distance in results]
    return [item for item in scored if item[1] >= score_threshold]


def delete_document_chunks(user_id: int, document_id: int) -> int:
    """
    删除某个文档在向量库中的全部切片

    Chroma 的 delete 只接受 ids，不支持按条件删，
    所以先按 metadata 查出 id 再删。

    Args:
        user_id: 用户主键
        document_id: 文档主键

    Returns:
        删除的向量条数
    """
    store = get_user_store(user_id)
    existing = store.get(where={"document_id": document_id}, include=[])
    ids = existing.get("ids") or []
    if not ids:
        return 0
    store.delete(ids=ids)
    return len(ids)


def count_user_chunks(user_id: int) -> int:
    """
    统计用户知识库中的切片总数

    Args:
        user_id: 用户主键

    Returns:
        切片条数
    """
    existing = get_user_store(user_id).get(include=[])
    return len(existing.get("ids") or [])


def delete_user_collection(user_id: int) -> None:
    """
    删除整个用户的知识库 collection

    用户注销时调用，确保向量数据不残留。

    Args:
        user_id: 用户主键
    """
    name = get_collection_name(user_id)
    try:
        get_user_store(user_id).delete_collection()
        logger.info(f"已删除用户 {user_id} 的知识库 collection: {name}")
    except Exception as e:
        # collection 尚未创建时会走到这里，属于正常情况
        logger.info(f"删除 collection {name} 时跳过: {e}")
    finally:
        # 缓存里必须同步移除，否则下次取到的是已删除 collection 的失效句柄
        with _store_lock:
            _user_stores.pop(user_id, None)


def list_user_collections(user_id: int) -> List[Dict[str, Any]]:
    
    """
    列出用户知识库 collection 的基本信息（用于后台排查）

    Args:
        user_id: 用户主键

    Returns:
        collection 名称与切片数
    """

    store = get_user_store(user_id)
    return [
        {
            "collection": store._collection.name,
            "chunks": count_user_chunks(user_id),
        }
    ]