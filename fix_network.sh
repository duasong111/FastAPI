#!/bin/bash

# 解决 Docker 容器网络连接问题

echo "🔍 检查当前 .env 配置..."
cat /home/FastProkect/.env

echo ""
echo "📋 检查 PostgreSQL 和 Redis 端口映射..."
docker ps | grep -E "postgres|redis"

echo ""
echo "🌐 检查 1panel-network 网络中的容器..."
docker network inspect 1panel-network | grep -A 5 "Name"

echo ""
echo "🔧 解决方案：将 PostgreSQL 和 Redis 加入网络..."

# 将 PostgreSQL 加入网络
docker network connect 1panel-network 1Panel-postgresql-iqTx 2>/dev/null && echo "✅ PostgreSQL 已加入网络" || echo "⚠️ PostgreSQL 可能已在网络中"

# 将 Redis 加入网络  
docker network connect 1panel-network 1Panel-redis-NGma 2>/dev/null && echo "✅ Redis 已加入网络" || echo "⚠️ Redis 可能已在网络中"

echo ""
echo "📝 更新 .env 文件使用容器名..."
cat > /home/FastProkect/.env << 'EOF'
DATABASE_URL=postgresql://user_rthXrh:password_prabtR@1Panel-postgresql-iqTx:5432/go_pg
REDIS_HOST=1Panel-redis-NGma
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
REDIS_DB=7
EOF

echo "✅ .env 已更新"
cat /home/FastProkect/.env

echo ""
echo "🔄 重启 FastAPI 容器..."
docker stop fastapi-app
docker rm fastapi-app

# 使用新的环境变量启动
source /home/FastProkect/.env
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

echo ""
echo "📋 查看日志..."
docker logs -f --tail 30 fastapi-app
