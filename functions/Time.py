"""
时间相关功能模块
提供多种格式的时间获取接口
"""
from datetime import datetime, timezone
from common.redis_cache import cache_result


@cache_result(key_prefix="time", expire_seconds=5)
def get_current_time_formats() -> dict:
    """
    获取当前时间的多种格式表示
    结果缓存 5 秒，减少服务器计算压力

    Returns:
        dict: 包含多种时间格式的字典
    """
    now = datetime.now()
    utc_now = datetime.now(timezone.utc)

    return {
        "iso_format": now.isoformat(),                          # ISO 8601 格式
        "utc_iso_format": utc_now.isoformat(),                  # UTC ISO 8601 格式
        "date_format": now.strftime("%Y-%m-%d"),                # 日期格式
        "time_format": now.strftime("%H:%M:%S"),                # 时间格式
        "datetime_format": now.strftime("%Y-%m-%d %H:%M:%S"),   # 日期时间格式
        "timestamp": int(now.timestamp()),                       # Unix 时间戳（秒）
        "timestamp_ms": int(now.timestamp() * 1000),            # Unix 时间戳（毫秒）
        "weekday": now.strftime("%A"),                           # 星期几（英文）
        "weekday_cn": _get_weekday_cn(now.weekday()),           # 星期几（中文）
        "timezone_offset": _get_timezone_offset(now),           # 时区偏移
        "cached": True,                                          # 标记数据来自缓存
    }


def _get_weekday_cn(weekday: int) -> str:
    """将数字星期转为中文"""
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[weekday]


def _get_timezone_offset(dt: datetime) -> str:
    """获取时区偏移量字符串"""
    offset = dt.utcoffset()
    if offset is None:
        return "UTC+8 (local assumed)"
    total_seconds = int(offset.total_seconds())
    hours, remainder = divmod(abs(total_seconds), 3600)
    minutes = remainder // 60
    sign = "+" if total_seconds >= 0 else "-"
    return f"UTC{sign}{hours:02d}:{minutes:02d}"
