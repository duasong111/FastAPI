#!/bin/bash

# FastAPI 部署脚本（加入 1panel-network 网络）

echo "🚀 开始部署 FastAPI 应用..."

# 1. 拉取最新镜像
echo "📦 拉取最新镜像..."
docker pull duasong111/fastapi-app:latest

# 2. 停止并删除旧容器
echo "🗑️ 停止旧容器..."
docker stop fastapi-app 2>/dev/null || true
docker rm fastapi-app 2>/dev/null || true

# 3. 检查并创建网络（确保与 PostgreSQL、Redis 在同一网络）
echo "🌐 检查 1panel-network 网络..."
if ! docker network ls | grep -q "1panel-network"; then
    echo "创建 1panel-network 网络..."
    docker network create 1panel-network
fi

# 4. 从 .env 文件读取环境变量并启动容器
echo "🚀 启动新容器（加入 1panel-network 网络）..."
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

# 5. 验证容器是否在同一网络
echo "🔍 验证网络连接..."
docker network inspect 1panel-network | grep -E '"Name": "fastapi-app|"Name": "1Panel-postgresql|"Name": "1Panel-redis'

# 6. 查看日志
echo "📋 查看启动日志..."
docker logs -f --tail 50 fastapi-app