from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from contextlib import asynccontextmanager
import logging

from functions.Time import get_current_time_formats
from functions.Weather import get_weather_data
from databases.database import get_db, init_db
from databases.models import TimeRequestLog, WeatherRequestLog
from common.redis_cache import rate_limit

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== 应用生命周期管理 ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动/关闭时自动执行

    启动时：检查并创建所有缺失的数据库表
    关闭时：清理资源（如需）
    """
    # 启动时执行
    _ = app  # 标记参数已使用
    logger.info("🚀 应用启动中，检查数据库表...")
    try:
        init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")

    yield

    # 关闭时执行（目前无需清理）
    logger.info("👋 应用关闭")


app = FastAPI(lifespan=lifespan)

# ============== CORS 跨境配置 ==============
# 允许所有来源、方法和头（开发环境）
# 生产环境应配置具体的 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # 允许所有来源，生产环境建议指定具体域名
    allow_credentials=True,           # 允许携带凭证（Cookie、Authorization header）
    allow_methods=["*"],              # 允许所有 HTTP 方法
    allow_headers=["*"],              # 允许所有请求头
    expose_headers=["*"],             # 暴露所有响应头给客户端
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.get("/api/get_time")
@rate_limit(key_prefix="api:get_time", max_requests=10, window_seconds=60)
async def get_time(request: Request, db: Session = Depends(get_db)):
    """
    获取当前时间的多种格式

    - 缓存策略：结果缓存 5 秒，减少重复计算
    - 速率限制：每个 IP 每分钟最多 10 次请求
    - 日志记录：每次请求记录到数据库

    返回ISO格式、日期时间格式、时间戳、星期等多种时间表示
    """
    # 记录请求日志
    log_entry = TimeRequestLog(
        request_time=datetime.now(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")
    )
    db.add(log_entry)
    db.commit()

    # 获取时间格式（自动使用 Redis 缓存）
    time_data = get_current_time_formats()

    return {
        "code": 200,
        "message": "success",
        "data": time_data
    }


@app.get("/api/weather")
@rate_limit(key_prefix="api:weather", max_requests=30, window_seconds=60)
async def get_weather(
    request: Request,
    db: Session = Depends(get_db),
    city: str = "武汉"
):
    """
    获取指定城市的天气信息

    - 缓存策略：结果缓存 1 小时，减少 API 调用
    - 速率限制：每个 IP 每分钟最多 30 次请求
    - 日志记录：每次请求记录到数据库

    Args:
        city: 城市名称，默认武汉

    Returns:
        天气数据（温度、湿度、风向、空气质量等）
    """
    # 记录请求日志
    log_entry = WeatherRequestLog(
        city=city,
        request_time=datetime.now(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")
    )
    db.add(log_entry)
    db.commit()

    # 获取天气数据（自动使用 Redis 缓存）
    weather_data = get_weather_data(city)

    return {
        "code": 200,
        "message": "success",
        "data": weather_data
    }


@app.exception_handler(Exception)
async def rate_limit_exception_handler(request: Request, exc: Exception):
    """处理速率限制异常"""
    if "Rate limit exceeded" in str(exc):
        return JSONResponse(
            status_code=429,
            content={
                "code": 429,
                "message": str(exc),
                "data": None
            }
        )
    # 其他异常
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": f"Internal server error: {str(exc)}",
            "data": None
        }
    )
