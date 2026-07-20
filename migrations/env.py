"""
迁移环境配置

提供数据库连接引擎，供各迁移文件使用
配置信息从 config.py 的 DATABASES 读取
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from config import DATABASES

# 从 config.py 获取数据库配置
db_config = DATABASES['default']
DATABASE_URL = (
    f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}"
    f"@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
)

# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=True)


def get_engine():
    """获取数据库引擎"""
    return engine