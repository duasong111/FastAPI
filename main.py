from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from contextlib import asynccontextmanager
import logging

from functions.Time import get_current_time_formats
from functions.Weather import get_weather_data
from functions.Knowledge import (
    DocumentNotFoundError,
    ask_question,
    delete_document,
    get_document,
    list_documents,
    upload_document,
)
from functions.Memory import clear_all_memories, delete_memory, list_memories
from functions.User import (
    AuthError,
    UserConflictError,
    build_user_data,
    get_user_by_id,
    login_user,
    register_user,
    resolve_user_from_token,
    update_llm_config,
)
from agent.ai.rag.ingest import IngestError
from common.llm import LLMConfigError
from common.memory import MemoryUnavailableError
from databases.database import get_db, init_db
from databases.models import TimeRequestLog, WeatherRequestLog, User
from common.redis_cache import rate_limit

# 引入序列化器
from Serializer.TimeSerializer import TimeData, TimeResponse
from Serializer.WeatherSerializer import (
    WeatherQueryRequest,
    WeatherData,
    WeatherResponse,
)
from Serializer.KnowledgeSerializer import (
    AskData,
    AskRequest,
    AskResponse,
    DeletedData,
    DeleteDocumentResponse,
    DocumentItem,
    DocumentListResponse,
    SourceItem,
    UploadResponse,
)
from Serializer.MemorySerializer import (
    DeleteMemoryResponse,
    DeletedMemoryData,
    MemoryItem,
    MemoryListData,
    MemoryListResponse,
    MemoryQueryRequest,
)
from Serializer.UserSerializer import (
    LLMConfigRequest,
    LLMConfigResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)

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


@app.get("/api/get_time", response_model=TimeResponse)
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
    time_dict = get_current_time_formats()
    time_data = TimeData(**time_dict)

    return TimeResponse(
        code=200,
        message="success",
        data=time_data
    )


@app.get("/api/weather", response_model=WeatherResponse)
@rate_limit(key_prefix="api:weather", max_requests=30, window_seconds=60)
async def get_weather(
    request: Request,
    db: Session = Depends(get_db),
    query: WeatherQueryRequest = Depends()
):
    """
    获取指定城市的天气信息

    - 缓存策略：结果缓存 1 小时，减少 API 调用
    - 速率限制：每个 IP 每分钟最多 30 次请求
    - 日志记录：每次请求记录到数据库
    """
    city = query.city

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
    weather_dict = get_weather_data(city)
    weather_data = WeatherData(**weather_dict)

    return WeatherResponse(
        code=200,
        message="success",
        data=weather_data
    )


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


# ============== 用户体系：依赖注入与异常处理 ==============

def get_current_user(
    authorization: str = Header(default="", description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> User:
    """
    登录态依赖：解析 Authorization 头，返回当前登录用户

    Raises:
        AuthError: 未携带令牌、令牌无效或已过期
    """
    if not authorization:
        raise AuthError("缺少登录凭证，请在请求头带上 Authorization: Bearer <token>")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("登录凭证格式错误，应为: Authorization: Bearer <token>")

    return resolve_user_from_token(db, parts[1])


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    """认证/授权失败"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.message, "data": None},
    )


@app.exception_handler(UserConflictError)
async def user_conflict_handler(request: Request, exc: UserConflictError):
    """用户名冲突"""
    return JSONResponse(
        status_code=409, content={"code": 409, "message": exc.message, "data": None}
    )


@app.exception_handler(DocumentNotFoundError)
async def document_not_found_handler(request: Request, exc: DocumentNotFoundError):
    """文档不存在"""
    return JSONResponse(
        status_code=404, content={"code": 404, "message": exc.message, "data": None}
    )


@app.exception_handler(IngestError)
async def ingest_error_handler(request: Request, exc: IngestError):
    """文档解析失败"""
    return JSONResponse(
        status_code=400, content={"code": 400, "message": str(exc), "data": None}
    )


@app.exception_handler(LLMConfigError)
async def llm_config_error_handler(request: Request, exc: LLMConfigError):
    """模型配置不合法"""
    return JSONResponse(
        status_code=400, content={"code": 400, "message": str(exc), "data": None}
    )


@app.exception_handler(MemoryUnavailableError)
async def memory_unavailable_handler(request: Request, exc: MemoryUnavailableError):
    """记忆功能不可用"""
    return JSONResponse(
        status_code=503, content={"code": 503, "message": str(exc), "data": None}
    )


# ============== 用户注册 / 登录 ==============

@app.post("/api/auth/register", response_model=RegisterResponse, tags=["用户"])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    注册新用户

    注册后即可用同一组用户名密码登录，并上传自己的大模型 API key。
    """
    user = register_user(db, payload.username, payload.password)
    return RegisterResponse(
        code=200, message="success", data=build_user_data(user)
    )


@app.post("/api/auth/login", response_model=LoginResponse, tags=["用户"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录，返回 JWT 令牌

    后续请求带上 `Authorization: Bearer <access_token>` 即可。
    """
    result = login_user(db, payload.username, payload.password)
    return LoginResponse(code=200, message="success", data=result)


@app.get("/api/auth/me", response_model=UserResponse, tags=["用户"])
def read_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse(code=200, message="success", data=build_user_data(current_user))


@app.put("/api/auth/llm-config", response_model=LLMConfigResponse, tags=["用户"])
def set_llm_config(
    payload: LLMConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传自己的大模型 API key（BYOK）

    key 用服务器端密钥加密后落库，任何接口都不会回显明文。
    换 key 或换服务商会让该用户此前的长期记忆失效并重建。
    """
    user = update_llm_config(
        db=db,
        user_id=current_user.id,
        provider=payload.provider,
        api_key=payload.api_key,
        model=payload.model,
    )
    return LLMConfigResponse(code=200, message="success", data=build_user_data(user))


# ============== 知识库：文档 ==============

@app.post("/api/knowledge/documents", response_model=UploadResponse, tags=["知识库"])
def upload_document_endpoint(
    file: UploadFile = File(..., description="支持 .txt / .md / .pdf，最大 20MB"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传文档到个人知识库

    文件会被解析、按中文标点切片、向量化后存入该用户专属的向量空间。
    """
    content = file.file.read()
    document = upload_document(
        db=db, user_id=current_user.id, filename=file.filename, content=content
    )
    return UploadResponse(
        code=200,
        message="success",
        data=DocumentItem(
            document_id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            chunk_count=document.chunk_count,
            status=document.status,
            created_at=document.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )


@app.get("/api/knowledge/documents", response_model=DocumentListResponse, tags=["知识库"])
def list_documents_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的全部文档"""
    documents = list_documents(db, current_user.id)
    return DocumentListResponse(
        code=200,
        message="success",
        data=[
            DocumentItem(
                document_id=d.id,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                chunk_count=d.chunk_count,
                status=d.status,
                created_at=d.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
            for d in documents
        ],
    )


@app.get(
    "/api/knowledge/documents/{document_id}", response_model=DocumentListResponse, tags=["知识库"]
)
def get_document_endpoint(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单个文档信息"""
    document = get_document(db, current_user.id, document_id)
    return DocumentListResponse(
        code=200,
        message="success",
        data=[
            DocumentItem(
                document_id=document.id,
                filename=document.filename,
                file_type=document.file_type,
                file_size=document.file_size,
                chunk_count=document.chunk_count,
                status=document.status,
                created_at=document.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        ],
    )


@app.delete(
    "/api/knowledge/documents/{document_id}",
    response_model=DeleteDocumentResponse,
    tags=["知识库"],
)
def delete_document_endpoint(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除文档，同时清理向量与原始文件"""
    deleted = delete_document(db, current_user.id, document_id)
    return DeleteDocumentResponse(
        code=200,
        message="success",
        data=DeletedData(document_id=document_id, deleted_chunks=deleted),
    )


# ============== 知识库：问答 ==============

@app.post("/api/knowledge/ask", response_model=AskResponse, tags=["知识库"])
def ask_endpoint(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    向个人知识库提问

    流程：召回长期记忆 → 向量检索文档片段 → 大模型作答 → 写入本轮新记忆。
    相同问题 1 小时内命中 Redis 缓存，不重复调用大模型。
    """
    result = ask_question(
        db=db,
        user_id=current_user.id,
        question=payload.question,
        top_k=payload.top_k,
        use_memory=payload.use_memory,
    )
    return AskResponse(
        code=200,
        message="success",
        data=AskData(
            answer=result["answer"],
            sources=[SourceItem(**s) for s in result["sources"]],
            memories_used=result["memories_used"],
            cached=result["cached"],
        ),
    )


# ============== 长期记忆 ==============

@app.get("/api/memory", response_model=MemoryListResponse, tags=["记忆"])
def list_memory_endpoint(
    query: str | None = None,
    top_k: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出或检索当前用户的长期记忆"""
    items = list_memories(db, current_user.id, query=query, top_k=top_k)
    return MemoryListResponse(
        code=200,
        message="success",
        data=MemoryListData(
            memories=[MemoryItem(**item) for item in items],
            total=len(items),
        ),
    )


@app.delete("/api/memory/{memory_id}", response_model=DeleteMemoryResponse, tags=["记忆"])
def delete_memory_endpoint(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除单条长期记忆"""
    total = delete_memory(db, current_user.id, memory_id)
    return DeleteMemoryResponse(
        code=200,
        message="success",
        data=DeletedMemoryData(memory_id=memory_id, total=total),
    )


@app.delete("/api/memory", response_model=DeleteMemoryResponse, tags=["记忆"])
def clear_memory_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空当前用户的全部长期记忆"""
    total = clear_all_memories(db, current_user.id)
    return DeleteMemoryResponse(
        code=200, message="success", data=DeletedMemoryData(memory_id=None, total=total)
    )
