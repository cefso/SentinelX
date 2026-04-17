# =============================================================================
# Stage 1: 生成版本文件
# =============================================================================
FROM alpine:3.19 AS builder

WORKDIR /app

# 复制 .git 用于获取 commit hash
COPY .git ./.git

# 生成版本文件
RUN apk add --no-cache bash coreutils git && \
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo unknown) && \
    GIT_SHORT=${GIT_COMMIT:0:7} && \
    BUILD_ID="${GIT_SHORT}-$(date +%Y%m%d-%H%M%S)" && \
    BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) && \
    echo "{\"git_commit\": \"$GIT_SHORT\", \"build_id\": \"$BUILD_ID\", \"build_time\": \"$BUILD_TIME\"}" > build-info.json && \
    cat build-info.json

# =============================================================================
# Stage 2: 运行应用
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
    && sed -i 's|http://security.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
    && apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# 从 Stage 1 复制版本文件
COPY --from=builder /app/build-info.json .

# backend-entrypoint.sh 已在上面的 COPY backend/ . 中复制到 /app
RUN chmod +x /app/backend-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/backend-entrypoint.sh"]
