"""
天气功能序列化器

定义天气相关的请求/响应数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


# ============== 请求模型 ==============

class WeatherQueryRequest(BaseModel):
    """
    天气查询请求参数

    Attributes:
        city: 城市名称，默认武汉
    """
    city: Optional[str] = Field(
        default="武汉",
        min_length=1,
        max_length=50,
        description="城市名称，默认武汉"
    )


# ============== 响应模型 ==============

class WeatherData(BaseModel):
    """
    天气数据模型

    Attributes:
        city: 城市名称
        weather: 天气状况
        temperature: 温度（摄氏度）
        humidity: 湿度百分比
        wind: 风向和风力
        air_quality: 空气质量
        update_time: 更新时间
        cached: 是否来自缓存
        source: 数据来源
    """
    city: str = Field(..., description="城市名称")
    weather: str = Field(..., description="天气状况")
    temperature: int = Field(..., ge=-50, le=60, description="温度（摄氏度）")
    humidity: int = Field(..., ge=0, le=100, description="湿度百分比")
    wind: str = Field(..., description="风向和风力")
    air_quality: str = Field(..., description="空气质量")
    update_time: str = Field(..., description="更新时间")
    cached: bool = Field(default=True, description="是否来自缓存")
    source: str = Field(default="api", description="数据来源")


class WeatherResponse(BaseModel):
    """
    天气查询统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 天气数据
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: WeatherData = Field(..., description="天气数据")