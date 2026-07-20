# common package
"""
公共工具模块
"""
from common.redis_cache import (
    RedisClient,
    get_redis,
    cache_result,
    clear_cache,
    rate_limit,
    CacheService  # 新增通用缓存服务
)

__all__ = [
    "RedisClient",
    "get_redis",
    "cache_result",
    "clear_cache",
    "rate_limit",
    "CacheService"
]