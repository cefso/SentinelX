#!/bin/bash
# SentinelX 数据库初始化脚本

set -e

echo "Initializing SentinelX database..."

# 创建TimescaleDB扩展
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

echo "Database extensions created successfully."

# 验证TimescaleDB
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT extname, extversion FROM pg_extension WHERE extname IN ('timescaledb', 'uuid-ossp');
EOSQL

echo "SentinelX database initialization complete."
