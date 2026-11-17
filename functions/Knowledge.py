"""
知识库功能模块

文档上传、列表、删除与问答的业务编排。

按分层规范，本模块只做编排：
- 切片与向量化交给 agent/ai/rag/ingest.py
- 检索与生成交给 agent/ai/rag/chain.py
- 向量库操作交给 common/vector_store.py
- 记忆交给 common/memory.py
- 缓存复用 common/redis_cache.CacheService
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

import common.vector_store as vector_store
from agent.ai.rag import chain as rag_chain
from agent.ai.rag import ingest as rag_ingest
from agent.ai.rag.ingest import IngestError
from common.memory import MemoryUnavailableError
from common.redis_cache import CacheService
from databases.models import AskLog, Document, DocumentChunk, User
from functions.User import AuthError, get_user_by_id

logger = logging.getLogger(__name__)

# 相同问题的回答缓存时长（秒）
ASK_CACHE_SECONDS = 3600


class DocumentNotFoundError(Exception):
    """文档不存在或不属于当前用户"""

    def __init__(self, message: str = "文档不存在"):
        super().__init__(message)
        self.message = message


# ============== 文档 ==============

def upload_document(
    db: Session,
    user_id: int,
    filename: str,
    content: bytes,
) -> Document:
    """
    上传并入库一个文档

    先建记录拿到 document_id，再用它做切片的元数据与文件名，
    这样 Chroma 里的每条向量都能反查到所属文档。

    Args:
        db: 数据库会话
        user_id: 用户主键
        filename: 原始文件名
        content: 文件二进制内容

    Returns:
        入库完成后的文档 ORM 对象

    Raises:
        IngestError: 文件类型不支持或解析失败
    """
    ext = rag_ingest.validate_upload(filename, len(content))

    document = Document(
        user_id=user_id,
        filename=filename,
        file_type=ext,
        file_size=len(content),
        chunk_count=0,
        status="processing",
    )
    db.add(document)
    # 先提交以拿到自增的 document_id，切片元数据要用它
    db.commit()
    db.refresh(document)

    try:
        chunks = rag_ingest.ingest_file(
            user_id=user_id,
            document_id=document.id,
            filename=filename,
            ext=ext,
            content=content,
        )
    except Exception:
        # 入库失败要把这条记录标成 failed，不能留下永远 processing 的脏数据
        document.status = "failed"
        document.chunk_count = 0
        db.commit()
        rag_ingest.delete_upload(user_id, document.id, ext)
        raise

    db.add_all([
        DocumentChunk(
            user_id=user_id,
            document_id=document.id,
            chunk_index=c["chunk_index"],
            content=c["content"],
            token_count=c["token_count"],
        )
        for c in chunks
    ])

    document.chunk_count = len(chunks)
    document.status = "ready"
    db.commit()
    db.refresh(document)

    logger.info(f"用户 {user_id} 上传文档成功: id={document.id}, 切片 {len(chunks)} 个")
    return document


def list_documents(db: Session, user_id: int) -> List[Document]:
    """
    列出用户的全部文档

    Args:
        db: 数据库会话
        user_id: 用户主键

    Returns:
        文档列表，按上传时间倒序
    """
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def get_document(db: Session, user_id: int, document_id: int) -> Document:
    """
    取文档并校验归属

    用 user_id 一起过滤，天然防止越权访问别人的文档。

    Args:
        db: 数据库会话
        user_id: 用户主键
        document_id: 文档主键

    Returns:
        文档 ORM 对象

    Raises:
        DocumentNotFoundError: 文档不存在或不属于该用户
    """
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )
    if document is None:
        raise DocumentNotFoundError()
    return document


def delete_document(db: Session, user_id: int, document_id: int) -> int:
    """
    删除文档：同时清理 Postgres 记录、Chroma 向量与原始文件

    Args:
        db: 数据库会话
        user_id: 用户主键
        document_id: 文档主键

    Returns:
        同步删除的向量片段数

    Raises:
        DocumentNotFoundError: 文档不存在或不属于该用户
    """
    document = get_document(db, user_id, document_id)

    deleted_chunks = vector_store.delete_document_chunks(user_id, document_id)
    rag_ingest.delete_upload(user_id, document_id, document.file_type)

    # document_chunks 有 ON DELETE CASCADE，删文档记录时切片记录会自动清掉
    db.delete(document)
    db.commit()

    logger.info(f"用户 {user_id} 删除文档: id={document_id}, 向量 {deleted_chunks} 条")
    return deleted_chunks


# ============== 问答 ==============

def _cache_key(user_id: int, question: str, top_k: int, use_memory: bool) -> str:
    """
    生成问答缓存键

    user_id 必须进 key，否则不同用户的相同问题会互相看到对方的回答。
    """
    digest = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()[:24]
    return f"kb:ask:{user_id}:{digest}:{top_k}:{int(use_memory)}"


def ask_question(
    db: Session,
    user_id: int,
    question: str,
    top_k: int = 5,
    use_memory: bool = True,
) -> Dict[str, Any]:
    """
    向知识库提问

    Args:
        db: 数据库会话
        user_id: 用户主键
        question: 用户问题
        top_k: 召回片段数
        use_memory: 是否启用长期记忆

    Returns:
        {"answer", "sources", "memories_used", "cached"}

    Raises:
        AuthError: 用户未配置大模型 key
        MemoryUnavailableError: 用户开启了记忆但记忆功能不可用
    """
    # 用户模型未配置时直接报错，这里先查一次，避免白跑一次检索
    get_user_by_id(db, user_id)

    cache_key = _cache_key(user_id, question, top_k, use_memory)
    cached = CacheService.get(cache_key)
    if cached:
        logger.info(f"问答命中缓存: user={user_id}, key={cache_key}")
        return {
            "answer": cached["answer"],
            "sources": cached["sources"],
            "memories_used": cached.get("memories_used", []),
            "cached": True,
        }

    # 延迟导入，避免 functions.Knowledge 与 functions.User 互相初始化
    from functions.Memory import get_memory_for_user
    from functions.User import get_user_chat_model

    chat_model = get_user_chat_model(db, user_id)

    memory = None
    if use_memory:
        try:
            memory = get_memory_for_user(db, user_id)
        except (MemoryUnavailableError, AuthError) as e:
            # 记忆是增强项，取不到就降级为无记忆问答，不该让整个请求失败
            logger.warning(f"记忆不可用，本次按无记忆问答: {e}")
            use_memory = False

    result = rag_chain.answer_question(
        user_id=user_id,
        question=question,
        chat_model=chat_model,
        top_k=top_k,
        use_memory=use_memory,
        memory=memory,
    )

    answer = result["answer"]
    sources = result["sources"]
    memories_used = result["memories_used"]

    # 写问答日志（失败不影响返回）
    try:
        db.add(AskLog(
            user_id=user_id,
            question=question,
            answer_preview=answer[:500],
            source_count=len(sources),
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"写问答日志失败: {e}")

    CacheService.set(
        key=cache_key,
        value={
            "answer": answer,
            "sources": sources,
            "memories_used": memories_used,
        },
        expire_seconds=ASK_CACHE_SECONDS,
    )

    return {
        "answer": answer,
        "sources": sources,
        "memories_used": memories_used,
        "cached": False,
    }