#!/bin/bash
# scripts/dev-init.sh
# 生成本地开发用版本文件

DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null) || GIT_COMMIT="local"
BUILD_ID="local-$(date +%Y%m%d-%H%M%S)"

BUILD_INFO="{\"git_commit\": \"$GIT_COMMIT\", \"build_id\": \"$BUILD_ID\", \"build_time\": \"$DATE\"}"

echo "$BUILD_INFO" > backend/build-info.json
echo "$BUILD_INFO" > frontend/public/build-info.json

echo "Version info generated:"
cat backend/build-info.json
