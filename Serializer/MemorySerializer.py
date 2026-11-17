"""
长期记忆功能序列化器

定义 Mem0 记忆的查询与删除相关的请求/响应数据模型
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ============== 请求模型 ==============

class MemoryQueryRequest(BaseModel):
    """
    记忆检索请求参数

    Attributes:
        query: 检索关键词，留空则列出全部记忆
        top_k: 召回条数
    """
    query: Optional[str] = Field(default=None, max_length=500, description="检索关键词，留空则列出全部")
    top_k: int = Field(default=20, ge=1, le=100, description="召回条数（1-100）")


# ============== 数据模型 ==============

class MemoryItem(BaseModel):
    """
    单条记忆数据模型

    Attributes:
        memory_id: 记忆条目 ID
        content: 记忆内容
        score: 检索得分
        created_at: 记忆创建时间
    """
    memory_id: Optional[str] = Field(default=None, description="记忆条目 ID")
    content: str = Field(..., description="记忆内容")
    score: Optional[float] = Field(default=None, description="检索得分")
    created_at: Optional[str] = Field(default=None, description="记忆创建时间")


class MemoryListData(BaseModel):
    """
    记忆列表数据模型

    Attributes:
        memories: 记忆条目列表
        total: 条目总数
    """
    memories: List[MemoryItem] = Field(default_factory=list, description="记忆条目列表")
    total: int = Field(default=0, description="条目总数")


class DeletedMemoryData(BaseModel):
    """
    记忆删除结果数据模型

    Attributes:
        memory_id: 被删除的记忆 ID，清空全部时为 None
        total: 本次删除的条数
    """
    memory_id: Optional[str] = Field(default=None, description="被删除的记忆 ID，清空全部时为 null")
    total: int = Field(default=0, description="本次删除的条数")


# ============== 响应模型 ==============

class MemoryListResponse(BaseModel):
    """
    记忆列表统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 记忆列表
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: MemoryListData = Field(..., description="记忆列表")


class DeleteMemoryResponse(BaseModel):
    """
    删除记忆统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 删除结果
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: DeletedMemoryData = Field(..., description="删除结果")