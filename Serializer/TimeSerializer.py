"""
时间功能序列化器

定义时间相关的响应数据模型
"""
from pydantic import BaseModel, Field


class TimeData(BaseModel):
    """
    时间数据模型

    Attributes:
        iso_format: ISO 8601 格式时间
        timestamp: Unix 时间戳（秒）
    """
    iso_format: str = Field(..., description="ISO 8601 格式时间")
    timestamp: int = Field(..., description="Unix 时间戳（秒）")


class TimeResponse(BaseModel):
    """
    时间查询统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 时间数据
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: TimeData = Field(..., description="时间数据")