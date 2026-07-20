#!/bin/bash

# FastAPI 部署脚本（解决 docker-compose 版本问题）

echo "🚀 开始部署 FastAPI 应用..."

# 1. 拉取最新镜像
echo "📦 拉取最新镜像..."
docker pull duasong111/fastapi-app:latest

# 2. 停止并删除旧容器
echo "🗑️ 停止旧容器..."
docker stop fastapi-app 2>/dev/null || true
docker rm fastapi-app 2>/dev/null || true

# 3. 从 .env 文件读取环境变量并启动容器
echo "🚀 启动新容器..."
source .env

docker run -d \
  --name fastapi-app \
  --restart unless-stopped \
  --network 1panel-network \
  -p 8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  -e REDIS_HOST="$REDIS_HOST" \
  -e REDIS_PORT="$REDIS_PORT" \
  -e REDIS_PASSWORD="$REDIS_PASSWORD" \
  -e REDIS_DB="$REDIS_DB" \
  duasong111/fastapi-app:latest

# 4. 查看日志
echo "📋 查看启动日志..."
docker logs -f --tail 50 fastapi-app