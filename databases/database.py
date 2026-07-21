# Database configuration
"""
数据库配置模块

配置信息从 config.py 的 DATABASES 获取
遵循 AI_DESIGN_SPECIFICATION.md 规范：禁止硬编码配置
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

from config import DATABASES

# 日志配置
logger = logging.getLogger(__name__)

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


def init_db():
    """
    初始化数据库：自动创建所有不存在的表

    遍历所有继承 Base 的模型，检查表是否存在，
    不存在则自动创建。后续新增模型只需继承 Base 即可自动建表。
    """
    try:
        # 获取数据库中已存在的表
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        # 获取所有模型定义的表
        all_models = Base.metadata.tables.keys()
        missing_tables = [t for t in all_models if t not in existing_tables]

        if missing_tables:
            logger.info(f"发现缺失的表: {missing_tables}，正在创建...")
            Base.metadata.create_all(bind=engine)
            logger.info(f"✅ 表创建成功: {missing_tables}")
        else:
            logger.info("✅ 所有表已存在，无需创建")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
