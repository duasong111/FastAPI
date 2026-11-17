"""RAG 检索增强生成模块

对外暴露文档摄取与问答两个入口，具体实现拆在：
- prompts.py  提示词模板
- ingest.py   文档解析与向量化入库
- chain.py    检索 + 生成的编排
"""
from agent.ai.rag.chain import (
    answer_question,
    build_messages,
    retrieve_context,
)
from agent.ai.rag.ingest import (
    IngestError,
    count_tokens,
    delete_upload,
    delete_user_upload_dir,
    ingest_file,
    split_into_chunks,
    validate_upload,
)

__all__ = [
    "answer_question",
    "build_messages",
    "retrieve_context",
    "IngestError",
    "count_tokens",
    "delete_upload",
    "delete_user_upload_dir",
    "ingest_file",
    "split_into_chunks",
    "validate_upload",
]