"""
知识库问答链

把「记忆检索 → 向量检索 → 拼提示词 → 大模型作答 → 写入新记忆」串成一条链。

大模型客户端由调用方传入（内部是用户自己的 key），
本模块不关心 key 从哪来，只负责编排。
"""
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

import common.memory as memory_mod
import common.vector_store as vector_store
from agent.ai.rag.prompts import (
    KB_MEMORY_SYSTEM_PROMPT,
    KB_SYSTEM_PROMPT,
    KB_USER_PROMPT,
    build_kb_context,
)

logger = logging.getLogger(__name__)

# 检索阶段的相关度下限，低于此值的片段不进入提示词
DEFAULT_SCORE_THRESHOLD = 0.3


def _format_source_name(doc) -> str:
    """
    生成片段的来源描述，用于提示词里的引用标注

    Args:
        doc: LangChain Document

    Returns:
        如 "README.md（片段 #3）" 或 "manual.pdf 第 2 页（片段 #3）"
    """
    meta = doc.metadata or {}
    filename = meta.get("filename", "未知文件")
    index = meta.get("chunk_index", 0)
    page = meta.get("page")
    if page is not None:
        return f"{filename} 第 {page} 页（片段 #{index}）"
    return f"{filename}（片段 #{index}）"


def retrieve_context(
    user_id: int,
    question: str,
    top_k: int = 5,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    从用户知识库检索相关切片

    Args:
        user_id: 用户主键
        question: 用户问题
        top_k: 召回数量
        score_threshold: 相似度下限

    Returns:
        [{"document": Document, "score": float, "source": str}, ...]
    """
    results = vector_store.search_documents(
        user_id=user_id,
        query=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )
    return [
        {
            "document": doc,
            "score": score,
            "source": _format_source_name(doc),
        }
        for doc, score in results
    ]


def build_messages(
    question: str,
    context_chunks: List[Dict[str, Any]],
    memory_block: str = "",
):
    """
    组装发给大模型的消息列表

    Args:
        question: 用户问题
        context_chunks: 检索到的知识库片段
        memory_block: Mem0 记忆段落，可为空

    Returns:
        [SystemMessage, HumanMessage]
    """
    context_text = build_kb_context(
        [(c["document"].page_content, c["source"]) for c in context_chunks]
    )

    if memory_block:
        system_prompt = KB_MEMORY_SYSTEM_PROMPT
        user_prompt = f"已知信息：\n{memory_block}\n\n" + KB_USER_PROMPT.format(
            context=context_text, question=question
        )
    else:
        system_prompt = KB_SYSTEM_PROMPT
        user_prompt = KB_USER_PROMPT.format(context=context_text, question=question)

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]


def answer_question(
    user_id: int,
    question: str,
    chat_model,
    top_k: int = 5,
    use_memory: bool = True,
    memory: Optional[Any] = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> Dict[str, Any]:
    """
    回答一次知识库提问

    Args:
        user_id: 用户主键
        question: 用户问题
        chat_model: LangChain 聊天模型实例（内部使用用户自己的 key）
        top_k: 召回片段数
        use_memory: 是否启用长期记忆
        memory: 该用户的 Mem0 实例；use_memory 为 True 时必传
        score_threshold: 相似度下限

    Returns:
        {
            "answer": str,
            "sources": [{"document_id", "filename", "chunk_index", "page", "content", "score", "source"}],
            "memories_used": [...],
        }

    Raises:
        ValueError: 开启了记忆但没有传 memory 实例
    """
    if use_memory and memory is None:
        raise ValueError("启用记忆时必须提供 Mem0 实例")

    # 1. 召回与当前问题相关的长期记忆
    memories: List[Dict[str, Any]] = []
    memory_block = ""
    if use_memory:
        memories = memory_mod.recall(memory, question)
        memory_block = memory_mod.format_memories_for_prompt(memories)

    # 2. 知识库向量检索
    context_chunks = retrieve_context(
        user_id=user_id,
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    # 3. 组装提示词并调用大模型
    messages = build_messages(question, context_chunks, memory_block)
    response = chat_model.invoke(messages)
    answer = response.content if hasattr(response, "content") else str(response)

    if not isinstance(answer, str):
        # 部分模型返回 content 为列表（多模态结构），这里只取文本部分
        answer = str(answer)

    # 4. 把这一轮对话交给 Mem0 提取长期记忆（失败不影响本次返回）
    if use_memory:
        memory_mod.remember(
            memory,
            user_id=user_id,
            messages=[
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
        )

    sources = []
    for chunk in context_chunks:
        doc = chunk["document"]
        meta = doc.metadata or {}
        sources.append({
            "document_id": meta.get("document_id"),
            "filename": meta.get("filename"),
            "chunk_index": meta.get("chunk_index"),
            "page": meta.get("page"),
            "content": doc.page_content,
            "score": round(chunk["score"], 4),
            "source": chunk["source"],
        })

    return {
        "answer": answer,
        "sources": sources,
        "memories_used": [
            m.get("memory") for m in memories if isinstance(m, dict) and m.get("memory")
        ],
    }