#!/bin/bash

# FastAPI 部署脚本

echo "🚀 开始部署 FastAPI 应用..."

# 1. 拉取最新镜像
echo "📦 拉取最新镜像..."
docker pull duasong111/fastapi-app:latest

# 2. 停止并删除旧容器
echo "🗑️ 停止旧容器..."
docker-compose down

# 3. 启动新容器
echo "🚀 启动新容器..."
docker-compose up -d

# 4. 查看日志
echo "📋 查看启动日志..."
docker-compose logs -f --tail=50