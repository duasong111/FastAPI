"""
Redis 缓存工具模块

提供 Redis 连接池和缓存装饰器
配置信息从 config.py 获取
"""
import redis
import json
import functools
from typing import Optional, Callable, Any, Dict
from datetime import timedelta

from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB


class RedisClient:
    """Redis 客户端单例"""
    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """获取 Redis 客户端实例（单例模式）"""
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                decode_responses=True,  # 自动解码为字符串
                socket_connect_timeout=5,  # 连接超时 5 秒
                socket_timeout=5,  # 操作超时 5 秒
                retry_on_timeout=True,  # 超时重试
            )
        return cls._instance


def get_redis() -> redis.Redis:
    """获取 Redis 客户端（用于 FastAPI 依赖注入）"""
    return RedisClient.get_client()


# ============== 通用缓存接口 ==============

class CacheService:
    """
    通用缓存服务类

    提供统一的缓存操作接口，所有业务模块可复用
    """

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值（自动 JSON 反序列化），不存在返回 None
        """
        try:
            redis_client = get_redis()
            value = redis_client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"⚠️ Redis get error: {e}")
            return None

    @staticmethod
    def set(key: str, value: Any, expire_seconds: int = 60) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值（自动 JSON 序列化）
            expire_seconds: 过期时间（秒）

        Returns:
            是否设置成功
        """
        try:
            redis_client = get_redis()
            redis_client.setex(
                key,
                expire_seconds,
                json.dumps(value, ensure_ascii=False)
            )
            return True
        except Exception as e:
            print(f"⚠️ Redis set error: {e}")
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        try:
            redis_client = get_redis()
            redis_client.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ Redis delete error: {e}")
            return False

    @staticmethod
    def exists(key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        try:
            redis_client = get_redis()
            return redis_client.exists(key) > 0
        except Exception as e:
            print(f"⚠️ Redis exists error: {e}")
            return False

    @staticmethod
    def get_or_set(key: str, fetch_func: Callable, expire_seconds: int = 60) -> Any:
        """
        获取缓存，不存在则调用函数获取并缓存

        Args:
            key: 缓存键
            fetch_func: 数据获取函数
            expire_seconds: 过期时间（秒）

        Returns:
            缓存值或函数返回值

        Usage:
            data = CacheService.get_or_set(
                "weather:wuhan",
                lambda: fetch_weather_from_api("武汉"),
                expire_seconds=3600
            )
        """
        # 先尝试从缓存获取
        cached_value = CacheService.get(key)
        if cached_value is not None:
            return cached_value

        # 缓存不存在，调用函数获取数据
        value = fetch_func()

        # 存入缓存
        CacheService.set(key, value, expire_seconds)

        return value

    @staticmethod
    def clear_pattern(pattern: str) -> int:
        """
        清除匹配模式的所有缓存

        Args:
            pattern: 键模式（支持通配符 *）

        Returns:
            删除的键数量
        """
        try:
            redis_client = get_redis()
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"⚠️ Redis clear_pattern error: {e}")
            return 0


def cache_result(
    key_prefix: str,
    expire_seconds: int = 60,
    key_builder: Optional[Callable] = None
):
    """
    缓存装饰器：缓存函数返回结果到 Redis
    
    Args:
        key_prefix: 缓存键前缀
        expire_seconds: 过期时间（秒）
        key_builder: 自定义键构建函数，接收 (*args, **kwargs)，返回缓存键后缀
    
    Usage:
        @cache_result("time", expire_seconds=5)
        def get_current_time_formats():
            return {"time": "2026-07-20"}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 构建 Redis 键
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                # 默认使用函数名作为后缀
                key_suffix = func.__name__
            
            cache_key = f"{key_prefix}:{key_suffix}"
            
            try:
                # 尝试从缓存获取
                redis_client = get_redis()
                cached_value = redis_client.get(cache_key)
                
                if cached_value is not None:
                    # 缓存命中，返回缓存数据
                    return json.loads(cached_value)
                
                # 缓存未命中，执行函数
                result = func(*args, **kwargs)
                
                # 存入缓存
                redis_client.setex(
                    cache_key,
                    expire_seconds,
                    json.dumps(result, ensure_ascii=False)
                )
                
                return result
                
            except Exception as e:
                # Redis 异常时，直接执行函数（降级处理）
                print(f"⚠️ Redis error: {e}, fallback to direct execution")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def clear_cache(key_pattern: str):
    """
    清除匹配模式的所有缓存
    
    Args:
        key_pattern: 键模式（支持通配符 *）
    
    Usage:
        clear_cache("time:*")  # 清除所有 time: 开头的缓存
    """
    try:
        redis_client = get_redis()
        keys = redis_client.keys(key_pattern)
        if keys:
            redis_client.delete(*keys)
            print(f"✅ Cleared {len(keys)} cache keys: {key_pattern}")
    except Exception as e:
        print(f"⚠️ Failed to clear cache: {e}")


def rate_limit(
    key_prefix: str,
    max_requests: int = 10,
    window_seconds: int = 60
):
    """
    速率限制装饰器：限制函数调用频率
    
    Args:
        key_prefix: 限流键前缀
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
    
    Usage:
        @rate_limit("api:get_time", max_requests=10, window_seconds=60)
        def get_time():
            return {"time": "2026-07-20"}
    
    Raises:
        Exception: 超过速率限制时抛出异常
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 提取请求对象（假设第一个参数是 Request）
            request = None
            for arg in args:
                if hasattr(arg, 'client'):  # FastAPI Request 对象
                    request = arg
                    break
            
            # 构建限流键（基于 IP）
            if request and request.client:
                client_ip = request.client.host
            else:
                client_ip = "unknown"
            
            limit_key = f"{key_prefix}:rate:{client_ip}"
            
            try:
                redis_client = get_redis()
                
                # 获取当前计数
                current_count = redis_client.get(limit_key)
                
                if current_count is None:
                    # 第一次请求，设置计数和过期时间
                    redis_client.setex(limit_key, window_seconds, 1)
                else:
                    current_count = int(current_count)
                    if current_count >= max_requests:
                        # 超过限制
                        ttl = redis_client.ttl(limit_key)
                        raise Exception(
                            f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s. "
                            f"Retry after {ttl}s."
                        )
                    # 增加计数
                    redis_client.incr(limit_key)
                
            except Exception as e:
                if "Rate limit exceeded" in str(e):
                    raise  # 重新抛出限流异常
                print(f"⚠️ Redis rate limit error: {e}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
