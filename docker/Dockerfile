FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 复制启动脚本
COPY backend-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/backend-entrypoint.sh

# 暴露端口
EXPOSE 8000

# 启动命令 - 先运行迁移，再启动应用
ENTRYPOINT ["/usr/local/bin/backend-entrypoint.sh"]
