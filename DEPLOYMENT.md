# FastAPI 项目部署文档

## 📋 部署流程

### 架构说明

```
本地电脑 (构建)          GitHub Actions (自动化)          服务器 (运行)
    │                          │                              │
    ├─ 编写代码 ──────────────►│                              │
    │                          ├─ 构建 Docker 镜像            │
    │                          ├─ 推送到 Docker Hub           │
    │                          │                              │
    │                          ├─ SSH 连接服务器 ─────────────►│
    │                          │                              ├─ 拉取镜像
    │                          │                              ├─ 停止旧容器
    │                          │                              ├─ 启动新容器
    │                          │                              └─ 清理旧镜像
```

---

## 🔧 第一步：配置 GitHub Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中添加以下密钥：

### Docker Hub 密钥

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `DOCKER_USERNAME` | Docker Hub 用户名 | `your-username` |
| `DOCKER_PASSWORD` | Docker Hub 密码或 Access Token | `dckr_pat_xxx` |

### 服务器 SSH 密钥

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `SERVER_HOST` | 服务器 IP 或域名 | `10.1.1.144` |
| `SERVER_USER` | SSH 用户名 | `root` |
| `SSH_PRIVATE_KEY` | SSH 私钥 | `-----BEGIN RSA PRIVATE KEY-----\n...` |

### 应用环境变量

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `DATABASE_URL` | 数据库连接 URL | `postgresql://user:pass@host:5432/db` |
| `REDIS_HOST` | Redis 主机 | `1Panel-redis-NGma` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | `your-password` |
| `REDIS_DB` | Redis 数据库编号 | `7` |

---

## 🚀 第二步：使用方式

### 方式一：完整流程（推荐）

```bash
# 1. 编写代码并提交
git add .
git commit -m "Add new feature"
git push origin main

# GitHub Actions 自动执行：
# ✅ 构建 Docker 镜像
# ✅ 推送到 Docker Hub
# ✅ SSH 到服务器拉取并部署
```

### 方式二：仅在本地构建（服务器内存不足时）

```bash
# 本地构建并推送
docker build -t your-username/fastapi-app:latest .
docker push your-username/fastapi-app:latest

# 服务器手动拉取并部署
ssh root@your-server

# 拉取最新镜像
docker pull your-username/fastapi-app:latest

# 停止并删除旧容器
docker stop fastapi-app || true
docker rm fastapi-app || true

# 启动新容器
docker run -d \
  --name fastapi-app \
  --restart unless-stopped \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e REDIS_HOST="your-redis-host" \
  -e REDIS_PORT="6379" \
  -e REDIS_PASSWORD="your-password" \
  -e REDIS_DB="7" \
  your-username/fastapi-app:latest
```

---

## ⚙️ 第三步：服务器初始化（首次部署）

### 1. 安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | bash

# 启动 Docker
systemctl start docker
systemctl enable docker
```

### 2. 创建网络（可选）

```bash
docker network create app-network
```

---

## 🔐 安全建议

### 1. 敏感信息处理

- ❌ **不要**将 `config.py` 中的密码提交到 GitHub
- ✅ 使用 GitHub Secrets 存储敏感信息
- ✅ 使用环境变量注入配置

### 2. SSH 密钥配置

```bash
# 本地生成 SSH 密钥对
ssh-keygen -t rsa -b 4096 -C "github-actions"

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github-actions.pub root@your-server

# 将私钥内容添加到 GitHub Secrets (SSH_PRIVATE_KEY)
cat ~/.ssh/github-actions
```

---

## 📊 监控与日志

### 查看容器日志

```bash
# 实时查看日志
docker logs -f fastapi-app

# 查看最近 100 行日志
docker logs --tail 100 fastapi-app
```

### 进入容器调试

```bash
docker exec -it fastapi-app /bin/bash
```

---

## 🔄 回滚操作

### 回滚到指定版本

```bash
# 查看镜像历史
docker images | grep fastapi-app

# 使用指定 SHA 的镜像
docker run -d \
  --name fastapi-app \
  -p 8000:8000 \
  your-username/fastapi-app:abc123
```

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `.github/workflows/docker-build.yml` | 构建并推送 Docker 镜像 |
| `.github/workflows/deploy.yml` | 自动部署到服务器 |
| `Dockerfile` | Docker 镜像构建配置 |
| `docker-compose.yml` | 本地开发环境配置 |
| `.env.example` | 环境变量示例文件 |

---

## ⚠️ 注意事项

1. **服务器内存优化**
   - Dockerfile 已优化，移除不必要的依赖
   - 使用 `gunicorn --workers 2` 限制进程数
   - 使用 `python:3.12-slim` 基础镜像

2. **GitHub Actions 缓存**
   - 使用 Docker Buildx 缓存加速构建
   - 缓存存储在 Docker Hub (`:buildcache` 标签)

3. **config.py 处理**
   - 生产环境通过环境变量覆盖配置
   - 代码中 `os.getenv()` 优先读取环境变量

---

**最后更新：** 2026-07-20
