# 使用 Python 3.12 slim 镜像（体积小）
FROM python:3.12-slim

WORKDIR /app

# 安装必要的系统依赖（重要！）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用阿里云镜像（加速）
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

# 生产环境使用 uvicorn（已解决 gunicorn 不可用问题）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]