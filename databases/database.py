# Database configuration
"""
数据库配置模块

配置信息从 config.py 的 DATABASES 获取
遵循 AI_DESIGN_SPECIFICATION.md 规范：禁止硬编码配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from config import DATABASES

# 从 config.py 的 DATABASES 配置构建数据库连接 URL
# 优先使用环境变量（Docker/K8s 部署场景），否则使用 config.py 配置
db_config = DATABASES['default']

# 构建数据库连接 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}"
    f"@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
