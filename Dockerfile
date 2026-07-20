# 使用 Python 3.12 slim 镜像（体积小）
FROM python:3.12-slim

WORKDIR /app

# 安装必要的系统依赖（PostgreSQL 客户端）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用阿里云镜像
RUN python -m pip install --upgrade pip
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip config set global.trusted-host mirrors.aliyun

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 环境变量
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# 生产环境使用 gunicorn（不用 --reload）
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]