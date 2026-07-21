# FastAPI 自动化 Docker 部署项目

> 基于 GitHub Actions 实现 CI/CD 自动构建与部署的 FastAPI 项目

---

## 📋 项目简介

本项目的目的是通过 **GitHub Actions** 实现自动化部署流程：

1. 本地编写代码并推送至 GitHub
2. GitHub Actions 自动构建 Docker 镜像
3. 镜像推送至 Docker Hub
4. 自动 SSH 连接服务器，拉取镜像并启动容器

---

## 📁 项目结构

```
FastAPI/
├── main.py                          # FastAPI 应用入口（路由注册）
├── config.py                        # 配置中心（数据库、Redis等）
├── requirements.txt                 # 项目依赖
├── Dockerfile                       # Docker 镜像构建配置
├── docker-compose.yml               # Docker Compose 配置
├── deploy.sh                        # 服务器部署脚本
├── stop.sh                          # 停止服务脚本
├── .env.example                     # 环境变量示例
├── .gitignore                       # Git 忽略规则
├── AI_DESIGN_SPECIFICATION.md       # AI 辅助开发设计规范
├── DEPLOYMENT.md                    # 部署文档
├── README.md                        # 本文件
├── .github/
│   └── workflows/
│       ├── docker-build.yml         # 构建并推送 Docker 镜像
│       └── deploy.yml               # 自动部署到服务器
├── functions/
│   ├── __init__.py
│   ├── Time.py                      # 时间功能模块
│   └── Weather.py                   # 天气查询功能模块
├── databases/
│   ├── __init__.py
│   ├── database.py                  # 数据库连接配置
│   └── models.py                    # ORM 模型定义
├── common/
│   ├── __init__.py
│   └── redis_cache.py               # Redis 缓存工具（通用缓存接口）
└── migrations/
    ├── __init__.py
    ├── env.py                       # 迁移环境配置
    └── versions/
        ├── __init__.py
        ├── 001_create_time_request_logs.py
        └── 002_create_weather_request_logs.py
```

---

## 🔧 环境配置

### 1. 本地开发环境

```bash
# 克隆项目
git clone https://github.com/你的用户名/FastAPI.git
cd FastAPI

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 配置文件说明

#### [config.py](config.py) - 配置中心

```python
# 正式环境（已启用）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'go_pg',
        'USER': 'user_rthXrh',
        'PASSWORD': 'password_prabtR',
        'HOST': '1Panel-postgresql-iqTx',  # 容器名（同一 Docker 网络）
        'PORT': '5432',
    }
}

REDIS_HOST = "1Panel-redis-NGma"  # 容器名（同一 Docker 网络）
REDIS_PORT = 6379
REDIS_PASSWORD = "redis_password"
REDIS_DB = 7
```

---

## 🚀 API 接口

### 根路径

```
GET / → {"message": "Hello World"}
```

### 时间接口

```
GET /api/get_time

响应示例：
{
    "code": 200,
    "message": "success",
    "data": {
        "iso_format": "2026-07-20T14:30:25.123456",
        "utc_iso_format": "2026-07-20T06:30:25.123456+00:00",
        "date_format": "2026-07-20",
        "time_format": "14:30:25",
        "datetime_format": "2026-07-20 14:30:25",
        "timestamp": 1782107425,
        "timestamp_ms": 1782107425123,
        "weekday": "Sunday",
        "weekday_cn": "星期日",
        "timezone_offset": "UTC+08:00",
        "cached": true
    }
}
```

- **缓存策略：** Redis 缓存 5 秒
- **速率限制：** 每个 IP 每分钟 10 次

### 天气接口

```
GET /api/weather?city=武汉

响应示例：
{
    "code": 200,
    "message": "success",
    "data": {
        "city": "武汉",
        "weather": "晴",
        "temperature": 28,
        "humidity": 65,
        "wind": "东风 3级",
        "air_quality": "良",
        "update_time": "2026-07-20 14:30:00",
        "cached": true,
        "source": "mock_api"
    }
}
```

- **缓存策略：** Redis 缓存 1 小时
- **速率限制：** 每个 IP 每分钟 30 次

---

## 💾 数据库

### 自动建表

应用启动时自动检查并创建缺失的数据库表：

```python
# databases/database.py
def init_db():
    """检查所有模型对应的表是否存在，不存在则自动创建"""
```

### 手动迁移

```bash
# 执行迁移
python migrations/versions/001_create_time_request_logs.py
python migrations/versions/002_create_weather_request_logs.py

# 回滚迁移
python migrations/versions/001_create_time_request_logs.py --downgrade
```

---

## 🛠️ Redis 缓存

### 通用缓存接口 `CacheService`

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

### 装饰器方式

```python
from common.redis_cache import cache_result, rate_limit

@cache_result(key_prefix="time", expire_seconds=5)
def get_current_time_formats():
    return {"time": "2026-07-20"}

@rate_limit(key_prefix="api:weather", max_requests=30, window_seconds=60)
async def get_weather(request: Request, ...):
    ...
```

---

## 🐳 Docker 部署

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 服务器部署脚本

#### [deploy.sh](deploy.sh) - 一键部署

```bash
#!/bin/bash
docker pull duasong111/fastapi-app:latest
docker stop fastapi-app || true
docker rm fastapi-app || true
docker run -d \
  --name fastapi-app \
  --restart unless-stopped \
  --network 1panel-network \       # 加入 1Panel 网络
  -p 8000:8000 \
  -e DATABASE_URL="..." \
  -e REDIS_HOST="1Panel-redis-NGma" \
  ... \
  duasong111/fastapi-app:latest
```

#### [stop.sh](stop.sh) - 停止服务

```bash
docker stop fastapi-app && docker rm fastapi-app
```

---

## 🔄 CI/CD 流水线

### 架构图

```
┌──────────────┐     git push     ┌──────────────────┐     SSH      ┌──────────────┐
│  本地电脑     │ ──────────────►  │  GitHub Actions  │ ──────────►  │   服务器     │
│  (编写代码)   │                 │  (构建镜像)       │             │  (运行容器)  │
└──────────────┘                 └──────────────────┘             └──────────────┘
                                         │                              │
                                         │ 推送至 Docker Hub            │ docker pull
                                         ▼                              ▼
                                   ┌──────────────┐             ┌──────────────┐
                                   │  Docker Hub  │             │  1Panel 网络  │
                                   │  (镜像仓库)   │             │  (容器通信)   │
                                   └──────────────┘             └──────────────┘
```

### 工作流文件

#### 1. 构建镜像 [docker-build.yml](.github/workflows/docker-build.yml)

- 触发条件：`push` 到 `main` 分支
- 构建 Docker 镜像并推送至 Docker Hub
- 使用 Buildx 缓存加速构建

#### 2. 部署到服务器 [deploy.yml](.github/workflows/deploy.yml)

- 依赖构建工作流成功
- SSH 连接服务器
- 拉取最新镜像并重启容器
- 容器加入 `1panel-network` 网络

---

## 🔐 配置 GitHub Secrets

在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `DOCKER_USERNAME` | Docker Hub 用户名 | `duasong111` |
| `DOCKER_PASSWORD` | Docker Hub 密码/Token | `dckr_pat_xxx` |
| `SERVER_HOST` | 服务器 IP | `10.1.1.144` |
| `SERVER_USER` | SSH 用户名 | `root` |
| `SSH_PRIVATE_KEY` | SSH 私钥 | `-----BEGIN RSA PRIVATE KEY-----` |
| `DATABASE_URL` | 数据库连接 URL | `postgresql://user:pass@host:5432/db` |
| `REDIS_HOST` | Redis 主机 | `1Panel-redis-NGma` |
| `REDIS_PASSWORD` | Redis 密码 | `redis_password` |

---

## 🌐 网络架构

### Docker 网络

```
┌────────────────────────────────────────────────────┐
│              1panel-network                        │
│                                                    │
│  ┌──────────────────┐    ┌──────────────────────┐  │
│  │  fastapi-app     │    │  PostgreSQL          │  │
│  │  (172.18.0.5)    │───▶│  (172.18.0.3)        │  │
│  │  端口: 8000      │    │  端口: 5432          │  │
│  └──────────────────┘    └──────────────────────┘  │
│           │                                        │
│           └────────────────────┐                   │
│                                ▼                   │
│                    ┌──────────────────────┐        │
│                    │  Redis               │        │
│                    │  (172.18.0.2)        │        │
│                    │  端口: 6379          │        │
│                    └──────────────────────┘        │
└────────────────────────────────────────────────────┘
```

所有容器通过 `1panel-network` 网络互相通信，使用**容器名**解析。

---

## 🚀 完整使用流程

### 第一次部署

```bash
# 1. 服务器安装 Docker
curl -fsSL https://get.docker.com | bash
systemctl start docker && systemctl enable docker

# 2. 确保 PostgreSQL 和 Redis 在 1panel-network 中
docker network connect 1panel-network 1Panel-postgresql-iqTx
docker network connect 1panel-network 1Panel-redis-NGma

# 3. 服务器创建部署目录
mkdir -p /home/FastProkect

# 4. 上传 .env 文件到 /home/FastProkect/
# 本地执行
scp .env root@服务器IP:/home/FastProkect/

# 5. 上传部署脚本
scp deploy.sh stop.sh root@服务器IP:/home/FastProkect/

# 6. 服务器部署
chmod +x /home/FastProkect/deploy.sh
/home/FastProkect/deploy.sh
```

### 日常更新

```bash
# 本地修改代码后
git add .
git commit -m "feat: add new feature"
git push origin main

# GitHub Actions 自动完成：
# ✅ 构建 Docker 镜像
# ✅ 推送至 Docker Hub
# ✅ SSH 部署到服务器
# ✅ 重启容器
```

### 服务器手动部署

```bash
cd /home/FastProkect
./deploy.sh
```

---

## 📊 验证部署

```bash
# 查看容器状态
docker ps | grep fastapi-app

# 查看日志
docker logs -f fastapi-app

# 测试接口
curl http://localhost:8000/api/get_time
curl http://localhost:8000/api/weather

# 查看网络连接
docker network inspect 1panel-network | grep -E "Name|IPv4Address"
```

---

## ⚠️ 注意事项

1. **网络连接：** 容器必须加入 `1panel-network` 网络才能通过容器名访问 PostgreSQL 和 Redis
2. **环境变量：** 生产环境通过 `.env` 文件或 GitHub Secrets 注入，`config.py` 中的配置会被覆盖
3. **数据库：** 应用启动时自动建表，无需手动迁移
4. **缓存：** Redis 不可用时自动降级，不影响服务正常运行
5. **安全：** `.env` 文件已加入 `.gitignore`，不会提交到 GitHub

---

## 📄 相关文档

- [AI_DESIGN_SPECIFICATION.md](AI_DESIGN_SPECIFICATION.md) - AI 辅助开发设计规范
- [DEPLOYMENT.md](DEPLOYMENT.md) - 详细部署文档

---

**最后更新：** 2026-07-21