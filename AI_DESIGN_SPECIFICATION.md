# AI 辅助开发设计规范

> 本文档定义了使用 AI 工具辅助开发本项目时必须遵守的规则和约定。所有 AI 生成的代码必须严格遵守本规范。

---

## 📌 核心原则

### 1. 项目结构约定

```
FastAPI/
├── main.py              # FastAPI 主应用入口，仅注册路由
├── config.py            # 所有配置信息集中管理
├── functions/           # 业务功能函数模块
│   ├── __init__.py
│   └── *.py             # 各功能模块
├── databases/           # 数据库相关
│   ├── __init__.py
│   ├── database.py      # 数据库连接配置
│   └── models.py        # ORM 模型定义
├── migrations/          # 数据库迁移文件（Python格式）
│   ├── __init__.py
│   └── versions/        # 迁移版本文件
└── requirements.txt     # 项目依赖
```

### 2. 配置管理规范

**所有配置必须从 `config.py` 获取，禁止硬编码配置信息。**

```python
# ✅ 正确做法
from config import DATABASES, REDIS_HOST, REDIS_PORT

# ❌ 错误做法
DATABASE_URL = "postgresql://user:pass@host:5432/db"  # 禁止硬编码
```

**数据库连接配置获取示例：**

```python
from config import DATABASES

db_config = DATABASES['default']
DATABASE_URL = f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
```

---

## 🗄️ 数据库迁移规范

### 1. 迁移文件格式

**迁移文件必须使用 Python 格式，存放在 `migrations/versions/` 目录下。**

**命名规则：** `{序号}_{描述}.py`

```
migrations/
├── __init__.py
├── env.py                    # 迁移环境配置
└── versions/
    ├── 001_create_time_request_logs.py
    ├── 002_add_user_table.py
    └── ...
```

### 2. 迁移文件模板

每个迁移文件必须包含 `upgrade()` 和 `downgrade()` 两个函数：

```python
"""
迁移文件模板
创建时间: {日期}
描述: {迁移描述}
"""
from sqlalchemy import text
from databases.database import engine
from config import DATABASES


def upgrade():
    """执行迁移"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS table_name (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()


def downgrade():
    """回滚迁移"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS table_name;"))
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

## 📝 代码规范

### 1. 函数定义规范

```python
# functions/Time.py
"""
时间相关功能模块
提供多种格式的时间获取接口
"""
from datetime import datetime, timezone


def get_current_time_formats() -> dict:
    """
    获取当前时间的多种格式表示

    Returns:
        dict: 包含多种时间格式的字典
            - iso_format: ISO 8601 格式
            - timestamp: Unix 时间戳
    """
    now = datetime.now()
    return {
        "iso_format": now.isoformat(),
        "timestamp": int(now.timestamp()),
    }
```

### 2. 路由定义规范

**路由逻辑写在 `main.py`，业务逻辑写在 `functions/` 模块中。**

```python
# main.py
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

from functions.Time import get_current_time_formats
from databases.database import get_db
from databases.models import TimeRequestLog

app = FastAPI()


@app.get("/api/get_time")
async def get_time(request: Request, db: Session = Depends(get_db)):
    """
    获取当前时间的多种格式
    """
    # 业务逻辑调用
    time_data = get_current_time_formats()
    
    # 数据库操作
    log_entry = TimeRequestLog(request_time=datetime.now())
    db.add(log_entry)
    db.commit()
    
    return {"code": 200, "data": time_data}
```

### 3. 数据库模型规范

```python
# databases/models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from databases.database import Base


class TimeRequestLog(Base):
    """时间接口请求日志表"""
    __tablename__ = "time_request_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_time = Column(DateTime, nullable=False, comment="请求时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<TimeRequestLog(id={self.id})>"
```

---

## 🎯 AI 行为准则

### AI 生成代码时必须：

1. **遵守项目结构** - 文件放在正确的目录
2. **使用 config.py** - 所有配置从 `config.py` 获取，禁止硬编码
3. **分离关注点** - 路由在 `main.py`，业务逻辑在 `functions/`
4. **完整迁移** - 迁移文件必须包含 `upgrade()` 和 `downgrade()`
5. **添加注释** - 函数、类、复杂逻辑必须有中文注释
6. **类型提示** - 函数参数和返回值必须有类型注解
7. **响应格式** - API 返回统一格式 `{"code": 200, "message": "", "data": {}}`

### AI 禁止行为：

- ❌ 硬编码数据库连接字符串
- ❌ 硬编码 Redis、RustFS 等配置信息
- ❌ 在迁移文件中使用非 Python 格式
- ❌ 创建不符合命名规范的文件或变量
- ❌ 省略必要的注释和类型提示

---

## 📋 响应格式规范

所有 API 接口统一返回格式：

```json
{
    "code": 200,
    "message": "success",
    "data": {
        // 业务数据
    }
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

## 🔧 依赖管理

新增依赖时必须：

1. 在 `requirements.txt` 中添加依赖及版本号
2. 使用国内镜像源：`https://mirrors.aliyun.com/pypi/simple/`
3. 注释说明依赖用途

```txt
# FastAPI and server
fastapi==0.115.6

# Database
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
```

---

## 📌 检查清单

AI 完成任务后，必须检查：

- [ ] 配置是否从 `config.py` 获取？
- [ ] 迁移文件是否使用 Python 格式？
- [ ] 是否包含 `upgrade()` 和 `downgrade()`？
- [ ] 函数是否有类型提示和注释？
- [ ] API 响应格式是否统一？
- [ ] 新增依赖是否添加到 `requirements.txt`？

---

**版本：** v1.0  
**更新日期：** 2026-07-20  
**适用项目：** FastAPI 自动化 Docker 部署项目