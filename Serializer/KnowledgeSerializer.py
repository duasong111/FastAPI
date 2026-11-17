"""
知识库功能序列化器

定义文档上传、列表、删除与问答相关的请求/响应数据模型
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ============== 请求模型 ==============

class AskRequest(BaseModel):
    """
    知识库提问请求参数

    Attributes:
        question: 用户问题
        top_k: 召回的文档片段数量
        use_memory: 是否启用长期记忆
    """
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    top_k: int = Field(default=5, ge=1, le=10, description="召回的文档片段数量（1-10）")
    use_memory: bool = Field(default=True, description="是否启用长期记忆")


# ============== 数据模型 ==============

class DocumentItem(BaseModel):
    """
    文档信息数据模型

    Attributes:
        document_id: 文档主键
        filename: 原始文件名
        file_type: 文件类型
        file_size: 文件大小（字节）
        chunk_count: 切片数
        status: 处理状态
        created_at: 上传时间
    """
    document_id: int = Field(..., description="文档主键")
    filename: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型: txt | md | pdf")
    file_size: int = Field(default=0, description="文件大小（字节）")
    chunk_count: int = Field(default=0, description="切分后的片段数")
    status: str = Field(..., description="处理状态: processing | ready | failed")
    created_at: str = Field(..., description="上传时间")


class SourceItem(BaseModel):
    """
    引用来源数据模型

    Attributes:
        document_id: 所属文档主键
        filename: 原始文件名
        chunk_index: 切片序号
        page: 页码，非 PDF 为 None
        content: 切片原文
        score: 相似度得分（越大越相关）
        source: 来源的可读描述
    """
    document_id: int = Field(..., description="所属文档主键")
    filename: str = Field(..., description="原始文件名")
    chunk_index: int = Field(..., description="切片序号（从 0 开始）")
    page: Optional[int] = Field(default=None, description="页码，非 PDF 为 None")
    content: str = Field(..., description="切片原文")
    score: float = Field(..., description="相似度得分（越大越相关）")
    source: str = Field(..., description="来源的可读描述")


class AskData(BaseModel):
    """
    问答结果数据模型

    Attributes:
        answer: 模型回答
        sources: 引用来源列表
        memories_used: 本次注入提示词的长期记忆
        cached: 是否命中 Redis 缓存
    """
    answer: str = Field(..., description="模型回答")
    sources: List[SourceItem] = Field(default_factory=list, description="引用来源列表")
    memories_used: List[str] = Field(default_factory=list, description="本次注入提示词的长期记忆")
    cached: bool = Field(default=False, description="是否命中 Redis 缓存")


class DeletedData(BaseModel):
    """
    删除操作结果数据模型

    Attributes:
        document_id: 被删除的文档主键
        deleted_chunks: 同步删除的向量片段数
    """
    document_id: int = Field(..., description="被删除的文档主键")
    deleted_chunks: int = Field(default=0, description="同步删除的向量片段数")


# ============== 响应模型 ==============

class UploadResponse(BaseModel):
    """
    文档上传统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 入库结果
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: DocumentItem = Field(..., description="入库结果")


class DocumentListResponse(BaseModel):
    """
    文档列表统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 文档列表
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: List[DocumentItem] = Field(..., description="文档列表")


class DeleteDocumentResponse(BaseModel):
    """
    删除文档统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 删除结果
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: DeletedData = Field(..., description="删除结果")


class AskResponse(BaseModel):
    """
    知识库问答统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 问答结果
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: AskData = Field(..., description="问答结果")