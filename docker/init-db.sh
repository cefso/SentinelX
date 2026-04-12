#!/bin/bash
# SentinelX 数据库初始化脚本
# 首次创建数据库时执行

set -e

echo "Initializing SentinelX database..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

# 安装 PGMQ 扩展 (SQL-only 模式，不依赖 deb)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /tmp/pgmq/pgmq-extension/sql/pgmq.sql

echo "Database extensions created successfully."

echo "SentinelX database initialization complete."
echo ""
echo "注意: 默认租户和超级管理员将在 Backend 首次启动时自动创建"
echo ""
