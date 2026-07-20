#!/bin/bash

# 停止服务

echo "🛑 停止 FastAPI 应用..."
docker stop fastapi-app 2>/dev/null || true
docker rm fastapi-app 2>/dev/null || true
echo "✅ 已停止"