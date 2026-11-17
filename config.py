# 配置有关的静态文件
import logging
import os
import secrets
from pathlib import Path
from typing import Callable, Optional

from cryptography.fernet import Fernet
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# .env 文件的键值（只读取，不注入 os.environ）
#
# 为什么不用 load_dotenv()：
# 本项目的 .env 里 DATABASE_URL 指向生产库（1panel-postgresql-* 容器名），
# 而 databases/database.py 用的是 os.getenv("DATABASE_URL", config.py 默认值)。
# 若把 .env 注入 os.environ，本地跑 uvicorn 会被导去连生产库。
# 因此这里只把 .env 当作"配置来源之一"读取，取值优先级仍为：
#     真实环境变量（容器内由 env_file 注入） > .env 文件 > 下面的默认值
_ENV_FILE_VALUES = dotenv_values(Path(__file__).parent / ".env")


def get_config(key: str, default: str = "") -> str:
    """
    读取配置项：环境变量 > .env 文件 > 默认值

    Args:
        key: 配置项名称
        default: 默认值

    Returns:
        配置值（均为字符串）
    """
    return os.getenv(key) or _ENV_FILE_VALUES.get(key) or default


def _require_secret(name: str, factory: Optional[Callable[[], str]] = None) -> str:
    """
    读取一个必须由运维显式配置的密钥。

    未配置时先生成一个随机值，保证本地开发能立刻跑起来，但会打印醒目警告——
    随机值意味着：服务每次重启都会换新，
    既会让所有已签发的 JWT 失效，也会让此前加密过的用户 LLM key 永久无法解密。
    因此生产环境必须在 .env 中固定这两个值。

    Args:
        name: 配置项名称
        factory: 随机值生成函数。Fernet 密钥有严格的格式要求，
                  不能用默认的 token_urlsafe，需由调用方传入专属生成器。

    Returns:
        配置值，或临时生成的随机值
    """
    logger.error(
        "❌ %s 未配置，已临时生成随机值。本地开发可继续，"
        "但生产环境必须在 .env 中固定该值，否则服务重启后："
        "① 所有登录态失效 ② 已加密的用户 LLM API key 永久无法解密。",
        name,
    )
    generate = factory or (lambda: secrets.token_urlsafe(48))
    return generate()


# 正式环境配置
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'user_rthXrh',
#         'PASSWORD': 'password_prabtR',
#         'HOST': '1Panel-postgresql-iqTx',
#         'PORT': '5432',
#     }
# }
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'user_rthXrh',
#         'PASSWORD': 'password_prabtR',
#         'HOST': '43.136.37.113',
#         'PORT': '5432',
#     }
# }


# 开发环境
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_pg',
        'USER': 'postgres',
        'PASSWORD': 'gsm200818534',
        'HOST': '10.1.1.136',
        'PORT': '5432',
    }
}

securityCode = "rewcef10fSd08FDS3ADVTSSA"
CODE_ERROR = 400
CODE_SUCCESS = 200

# 正式环境配置
# REDIS_HOST = "1Panel-redis-NGma"
# REDIS_PORT = 6379
# REDIS_PASSWORD = "redis_password"
# REDIS_DB = 7


# 开发环境配置
REDIS_HOST = "10.1.1.136"
REDIS_PORT = 6379
REDIS_PASSWORD = "gsm200818534"
REDIS_DB = 7

REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# 正式环境 设置桶
# BUCKET_IP = "43.136.37.113"
# BUCKET_PORT = "9000"
# RUSTFS_BUCKET_NAME = "rustfsadmin"
# RUSTFS_SECRET = "rustfsadmin_8bGjFM"

# 测试环境下的
BUCKET_IP = "10.1.1.234"
BUCKET_PORT = "9000"
RUSTFS_BUCKET_NAME = "rustfsadmin"
RUSTFS_SECRET = "rustfsadmin_WjQX2J"

# 用户头像桶（需要新建桶或在 RUSTFS 控制台创建）
AVATAR_BUCKET_NAME = "avatar"


# ============== LLM 聊天模型（BYOK：用户自带 key）==============
# 服务器不持有任何聊天大模型的 key。用户注册后自行上传，
# 加密后存进 users 表，由 common/llm.py 在其请求内解密使用。
#
# DeepSeek 与 MiniMax 均为 OpenAI 兼容协议，因此 common/llm.py 里
# 两者共用 ChatOpenAI，只换 base_url / model / api_key。
# 这里只登记服务商的接口地址与模型清单。

LLM_PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    # ⚠️ base_url 与模型名未联网核实，若 MiniMax 控制台给出的不同，改这里即可
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "models": ["MiniMax-Text-01"],
        "default_model": "MiniMax-Text-01",
    },
}

# 未指定服务商时使用的默认值（用户可在注册后自行切换）
DEFAULT_LLM_PROVIDER = get_config("LLM_PROVIDER", "deepseek")


# ============== Embedding 向量模型 ==============
# DeepSeek 不提供 embedding 接口，向量模型单独走硅基流动（免费、中文友好）
# 接口文档: https://docs.siliconflow.cn
#
# 这里的 key 由服务器统一持有、所有用户共用（免费额度，成本可忽略），
# 服务端与 Mem0 的记忆向量都复用它。
SILICONFLOW_API_KEY = get_config("sk-blztcjiaubzgxgculzhvpjshmpeokgcvtjjwkwhtzsrutbet")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_EMBED_MODEL = "BAAI/bge-m3"


# ============== Mem0 长期记忆 ==============
# 记忆向量库独立存放，与知识库向量互不影响
MEM0_PERSIST_DIR = get_config("MEM0_PERSIST_DIR", "./data/chroma_mem0")
# 单个用户的记忆最多召回多少条注入到提示词里
MEM0_TOP_K = int(get_config("MEM0_TOP_K", "5"))
# 对话历史在触发记忆提取前保留的最近几轮
MEM0_HISTORY_TURNS = int(get_config("MEM0_HISTORY_TURNS", "6"))


# ============== 用户认证 ==============
# JWT 签名密钥。生产环境必须设置为固定值，否则重启后所有登录态失效。
JWT_SECRET = get_config("JWT_SECRET") or _require_secret("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(get_config("JWT_EXPIRE_MINUTES", "1440"))  # 默认 24 小时

# 用于加密用户自带的 LLM API key（Fernet / AES-128-CBC + HMAC）。
# 生成方式: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
KB_ENCRYPTION_KEY = get_config("KB_ENCRYPTION_KEY") or _require_secret(
    "KB_ENCRYPTION_KEY",
    # Fernet 密钥必须是 32 字节的 urlsafe-base64，不能用默认的 token_urlsafe
    factory=lambda: Fernet.generate_key().decode(),
)


# ============== 文本切片 ==============
# 中英文混排文档，切片分隔符按中文标点优先，避免把句子从中间切断
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
CHUNK_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


# ============== 向量库（ChromaDB）持久化 ==============
# Docker 部署时必须挂载 volume，否则容器重建后向量数据全丢
CHROMA_PERSIST_DIR = get_config("CHROMA_PERSIST_DIR", "./data/chroma")
# 每个用户一个 collection，物理隔离
CHROMA_COLLECTION_PREFIX = "kb_user_"
# 用户上传的原始文件存放目录
UPLOAD_DIR = get_config("UPLOAD_DIR", "./data/uploads")
# 允许上传的文件扩展名
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
# 单个文件大小上限（字节），默认 20MB
MAX_UPLOAD_SIZE = 20 * 1024 * 1024

