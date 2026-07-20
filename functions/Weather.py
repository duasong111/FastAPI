"""
天气查询功能模块

提供天气查询接口，支持缓存
"""
import requests
from typing import Dict, Optional
from common.redis_cache import CacheService


def get_weather_data(city: str = "武汉") -> Dict:
    """
    获取指定城市的天气信息

    Args:
        city: 城市名称，默认武汉

    Returns:
        天气数据字典
    """
    # 缓存键
    cache_key = f"weather:{city}"

    # 使用通用缓存接口：缓存1小时
    def fetch_weather():
        """从 API 获取天气数据"""
        try:
            # 使用免费的天气 API（示例）
            # 实际项目中应替换为真实的天气 API
            # 这里使用模拟数据作为示例
            weather_data = _fetch_weather_from_api(city)
            return weather_data
        except Exception as e:
            print(f"⚠️ Failed to fetch weather: {e}")
            return _get_mock_weather_data(city)

    return CacheService.get_or_set(
        cache_key,
        fetch_weather,
        expire_seconds=3600  # 缓存 1 小时
    )


def _fetch_weather_from_api(city: str) -> Dict:
    """
    从天气 API 获取数据

    实际项目中替换为真实的天气 API
    """
    # 示例：使用免费的天气 API
    # API 地址示例：https://api.open-meteo.com/v1/forecast
    # 或使用心知天气、和风天气等国内服务

    # 这里返回模拟数据
    return _get_mock_weather_data(city)


def _get_mock_weather_data(city: str) -> Dict:
    """
    获取模拟天气数据（开发测试用）

    实际部署时替换为真实 API 调用
    """
    from datetime import datetime
    import random

    weather_types = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雷阵雨"]

    return {
        "city": city,
        "weather": random.choice(weather_types),
        "temperature": random.randint(20, 35),
        "humidity": random.randint(40, 80),
        "wind": f"{random.choice(['东风', '南风', '西风', '北风'])} {random.randint(1, 5)}级",
        "air_quality": random.choice(["优", "良", "轻度污染"]),
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cached": True,  # 标记数据来源
        "source": "mock_api"  # 数据来源标识
    }