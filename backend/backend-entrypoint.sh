#!/bin/bash
# SentinelX Backend 启动脚本
# 确保数据库迁移始终是最新的

set -e

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete. Starting application..."

exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
