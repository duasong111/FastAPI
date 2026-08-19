# AI 辅助开发设计规范（总纲）

> 本文档定义了使用 AI 工具辅助开发本项目时必须遵守的完整规则和约定。
> 所有 AI 生成的代码必须严格遵守本规范。
> **文档版本：** v2.0 | **最后更新：** 2026-07-21

---

## 📌 第一部分：核心原则

### 1. 项目结构约定

```
FastAPI/
├── main.py                      # FastAPI 主应用入口，仅注册路由
├── config.py                    # 所有配置信息集中管理
├── requirements.txt             # 项目依赖（顶层依赖，不锁版本）
├── Dockerfile                   # Docker 镜像配置
├── docker-compose.yml           # Docker Compose 配置
├── deploy.sh                    # 服务器部署脚本
├── stop.sh                      # 停止服务脚本
├── .env.example                 # 环境变量示例
├── .gitignore                   # Git 忽略规则
├── README.md                    # 项目说明文档
│
├── functions/                   # 业务功能函数模块
│   ├── __init__.py
│   ├── Time.py                  # 时间功能
│   ├── Weather.py               # 天气功能
│   └── *.py                     # 各功能模块
│
├── databases/                   # 数据库相关
│   ├── __init__.py
│   ├── database.py              # 数据库连接配置
│   └── models.py                # ORM 模型定义
│
├── Serializer/                  # 序列化器模块（请求/响应数据模型）
│   ├── __init__.py
│   ├── WeatherSerializer.py     # 天气序列化器
│   ├── TimeSerializer.py        # 时间序列化器
│   └── *.py                     # 各功能序列化器
│
├── common/                      # 公共工具模块
│   ├── __init__.py
│   └── redis_cache.py           # Redis 缓存工具（通用接口）
│
├── migrations/                  # 数据库迁移文件（Python 格式）
│   ├── __init__.py
│   ├── env.py                   # 迁移环境配置
│   └── versions/
│       ├── __init__.py
│       └── *.py                 # 各迁移版本
│
└── .github/
    └── workflows/
        ├── docker-build.yml     # 构建 Docker 镜像
        └── deploy.yml           # 部署到服务器
```

---

### 2. 关注点分离原则

| 层 | 职责 | 位置 |
|----|------|------|
| **路由层** | URL 路由、参数接收 | `main.py` |
| **业务逻辑层** | 核心业务处理 | `functions/` |
| **数据访问层** | 数据库 CRUD | `databases/` |
| **序列化层** | 数据格式验证 | `Serializer/` |
| **通用工具层** | 缓存、限流等公共功能 | `common/` |

**禁止跨层调用：**
- ❌ Serializer 中不能写业务逻辑
- ❌ functions 中不能直接操作数据库（应通过依赖注入）
- ❌ databases 中不能写业务逻辑

---

## 📌 第二部分：配置管理规范

### 所有配置必须从 `config.py` 获取

```python
# ✅ 正确做法
from config import DATABASES, REDIS_HOST, REDIS_PORT

# ❌ 错误做法
DATABASE_URL = "postgresql://user:pass@host:5432/db"  # 禁止硬编码
```

### 数据库连接配置

```python
from config import DATABASES

db_config = DATABASES['default']
DATABASE_URL = (
    f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}"
    f"@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
)
```

### 环境变量优先（容器化部署）

```python
import os
DATABASE_URL = os.getenv("DATABASE_URL", default_value_from_config)
```

---

## 📌 第三部分：Serializer 序列化器规范

### 1. 文件命名规范

**每个具体功能对应一个独立的 .py 文件：**

```
Serializer/
├── __init__.py
├── WeatherSerializer.py        # 天气功能的序列化器
├── TimeSerializer.py           # 时间功能的序列化器
├── UserSerializer.py           # 用户功能的序列化器
```

**命名要求：**
- 文件名必须以 `Serializer` 结尾
- 使用帕斯卡命名法（PascalCase）
- 一个文件只对应一个功能

---

### 2. 文件内部结构

每个序列化器文件必须包含以下结构：

```python
"""
[功能名称]序列化器

定义[功能]相关的请求/响应数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


# ============== 请求模型 ==============

class [功能]Request(BaseModel):
    """
    [功能]请求参数

    Attributes:
        [字段]: [说明]
    """
    [字段名]: [类型] = Field(..., description="[说明]")


# ============== 响应模型 ==============

class [功能]Data(BaseModel):
    """
    [功能]数据模型

    Attributes:
        [字段]: [说明]
    """
    [字段名]: [类型] = Field(..., description="[说明]")


class [功能]Response(BaseModel):
    """
    [功能]统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 数据
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: [功能]Data = Field(..., description="数据")
```

---

### 3. Serializer 必须遵守

| 规则 | 说明 |
|------|------|
| ✅ 文件必须有 docstring | 文件顶部说明功能 |
| ✅ 类必须有 docstring | 说明用途 |
| ✅ 字段必须有 description | 描述字段含义 |
| ✅ 类属性使用 Field | `field: type = Field(...)` |
| ✅ 响应模型统一格式 | code/message/data 三件套 |
| ✅ 中文注释 | 所有说明用中文 |

### 4. Serializer 禁止做的事

| 禁止 | 原因 |
|------|------|
| ❌ 业务逻辑 | Serializer 只负责数据格式 |
| ❌ 数据库操作 | 数据访问放在 databases/ |
| ❌ 缓存操作 | 缓存操作放在 common/ |
| ❌ 硬编码配置 | 配置从 config.py 读取 |
| ❌ 多个功能混合 | 一个文件只对应一个功能 |

---

### 5. 字段定义规范

```python
# 必填字段
field_name: type = Field(..., description="说明")

# 可选字段
field_name: Optional[type] = Field(default=默认值, description="说明")

# 长度限制
name: str = Field(..., min_length=1, max_length=50, description="名称")

# 数值范围
age: int = Field(..., ge=0, le=150, description="年龄")

# 邮箱验证
email: EmailStr = Field(..., description="邮箱")
```

---

## 📌 第四部分：Functions 业务逻辑规范

### 1. 文件命名规范

```
functions/
├── __init__.py
├── Time.py              # 时间功能
├── Weather.py           # 天气功能
└── *.py
```

**命名要求：**
- 文件名直接使用功能名（不加后缀）
- 使用帕斯卡命名法

### 2. 函数编写规范

```python
"""
[功能名称]功能模块

[功能详细说明]
"""
from typing import Dict


def get_function_data(param: str) -> Dict:
    """
    [函数功能说明]

    Args:
        param: 参数说明

    Returns:
        返回值说明
    """
    return {"data": "value"}
```

---

## 📌 第五部分：Databases 数据库规范

### 1. 模型文件规范

```python
# databases/models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from databases.database import Base


class ExampleModel(Base):
    """模型说明"""
    __tablename__ = "example_table"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="名称")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<ExampleModel(id={self.id})>"
```

### 2. 数据库连接规范

```python
# databases/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from config import DATABASES

db_config = DATABASES['default']
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
```

---

## 📌 第六部分：Migrations 数据库迁移规范

### 1. 迁移文件格式

**必须使用 Python 格式，存放在 `migrations/versions/` 目录下。**

**命名规则：** `{序号}_{描述}.py`

```
migrations/
├── __init__.py
├── env.py                    # 迁移环境配置
└── versions/
    ├── 001_create_time_request_logs.py
    └── ...
```

### 2. 迁移文件模板

每个迁移文件必须包含 `upgrade()` 和 `downgrade()` 两个函数：

```python
"""
迁移文件: 001_xxx
描述: xxx

数据库配置从 config.py 的 DATABASES 获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from migrations.env import get_engine


def upgrade():
    """执行迁移"""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS xxx (
                id SERIAL PRIMARY KEY,
                ...
            );
        """))
        conn.commit()


def downgrade():
    """回滚迁移"""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS xxx;"))
        conn.commit()
```

### 3. 迁移文件必须遵守

- ✅ 从 `config.py` 读取数据库配置
- ✅ 使用 SQLAlchemy 的 `text()` 执行原生 SQL
- ✅ 同时提供 `upgrade()` 和 `downgrade()`
- ✅ 包含清晰的注释说明迁移目的
- ✅ 表名使用蛇形命名法 (snake_case)
- ✅ 每个表必须有主键 `id` 和创建时间 `created_at`

---

## 📌 第七部分：Common 公共工具规范

### 1. 通用缓存接口

**所有需要缓存的业务都使用 `CacheService`：**

```python
from common.redis_cache import CacheService

# 获取或设置缓存
data = CacheService.get_or_set(
    key="weather:wuhan",
    fetch_func=lambda: fetch_from_api(),
    expire_seconds=3600
)

# 手动缓存操作
CacheService.set("key", value, expire_seconds=60)
CacheService.get("key")
CacheService.delete("key")
CacheService.exists("key")

# 批量清除
CacheService.clear_pattern("weather:*")
```

### 2. Redis 连接配置

**Redis 配置必须从 `config.py` 获取：**

```python
from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
```

---

## 📌 第八部分：路由规范

### 1. 路由必须在 main.py 中定义

```python
# main.py
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

from functions.Time import get_current_time_formats
from Serializer.TimeSerializer import TimeResponse
from databases.database import get_db

app = FastAPI()


@app.get("/api/get_time", response_model=TimeResponse)
async def get_time(request: Request, db: Session = Depends(get_db)):
    """获取时间"""
    time_data = get_current_time_formats()
    return TimeResponse(code=200, message="success", data=time_data)
```

### 2. 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "data": {}
}
```

错误响应：

```json
{
    "code": 400,
    "message": "错误描述",
    "data": null
}
```

---

## 📌 第九部分：依赖管理规范

### requirements.txt 规范

**只写顶层依赖，不锁版本，让 pip 自动解析子依赖：**

```txt
# ✅ 推荐：不锁版本
fastapi
uvicorn
gunicorn
sqlalchemy
psycopg2-binary
redis
python-multipart

# ❌ 不推荐：锁所有版本
fastapi==0.139.2
annotated-doc==0.0.4
annotated-types==0.7.0
...
```

**理由：**
- 新增依赖只需在 `requirements.txt` 加一行
- pip 会自动解析最新兼容版本
- 无需手动执行 `pip freeze`

---

## 📌 第十部分：Docker 部署规范

### 1. Dockerfile 规范

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 容器网络规范

**所有业务容器必须加入 `1panel-network` 网络：**

```bash
docker run -d \
  --name fastapi-app \
  --network 1panel-network \
  ...
```

---

## 📌 第十一部分：AI 行为准则

### ✅ AI 生成代码时必须：

1. **遵守项目结构** - 文件放在正确的目录
2. **使用 config.py** - 所有配置从 `config.py` 获取
3. **分离关注点** - 路由、业务、数据、序列化分离
4. **Serializer 规范** - 遵循 Serializer 文件命名和结构
5. **完整注释** - 函数、类、字段必须有中文注释
6. **类型注解** - 函数参数和返回值必须有类型注解
7. **响应格式统一** - API 返回 `{"code", "message", "data"}`
8. **顶层依赖** - requirements.txt 不锁版本

### ❌ AI 禁止行为：

1. **硬编码配置** - 禁止硬编码数据库连接字符串
2. **混合关注点** - Serializer 中写业务逻辑
3. **手动迁移文件** - 迁移必须用 Python 格式
4. **忽略注释** - 必须写中文注释
5. **锁版本** - requirements.txt 只写顶层依赖
6. **跨层调用** - functions 直接操作数据库

---

## 📌 第十二部分：检查清单

AI 完成任务后必须自检：

### 文件结构

- [ ] 文件是否放在正确的目录？
- [ ] 文件名是否符合命名规范？
- [ ] 是否避免了跨层调用？

### 代码规范

- [ ] 配置是否从 `config.py` 获取？
- [ ] 函数是否有类型提示？
- [ ] 是否有中文注释？
- [ ] 是否避免了硬编码？

### Serializer

- [ ] 文件名是否以 `Serializer` 结尾？
- [ ] 类是否有 docstring？
- [ ] 字段是否使用 `Field(...)` 定义？
- [ ] 响应模型是否包含 `code/message/data`？

### 数据库

- [ ] 迁移文件是否使用 Python 格式？
- [ ] 是否包含 `upgrade()` 和 `downgrade()`？
- [ ] 表名是否使用 snake_case？

### 部署

- [ ] requirements.txt 是否只写顶层依赖？
- [ ] Dockerfile 是否配置了 pip 镜像？
- [ ] 容器是否加入正确的网络？

---

## 📌 第十三部分：完整调用示例

### 一个完整功能的代码结构

```
# Serializer/WeatherSerializer.py - 数据模型
class WeatherData(BaseModel):
    city: str
    temperature: int

# functions/Weather.py - 业务逻辑
def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 28}

# main.py - 路由
from Serializer.WeatherSerializer import WeatherData, WeatherResponse
from functions.Weather import get_weather

@app.get("/api/weather", response_model=WeatherResponse)
async def weather(query: WeatherQueryRequest = Depends()):
    data = get_weather(query.city)
    return WeatherResponse(code=200, message="success", data=data)
```

---

## 🔗 相关文档

- [README.md](README.md) - 项目说明
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署文档
- [Serializer/SERIALIZER_SPECIFICATION.md](Serializer/SERIALIZER_SPECIFICATION.md) - Serializer 详细规范

---

**版本：** v2.0
**最后更新：** 2026-07-21
**适用项目：** FastAPI 自动化 Docker 部署项目