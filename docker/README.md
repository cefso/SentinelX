# SentinelX Docker 部署配置

> 详细的 API 文档和部署指南请参考项目根目录 `docs/API.md` 和 `docs/DEPLOYMENT.md`。

## Docker Compose 文件

| 文件 | 说明 | 使用场景 |
|------|------|---------|
| `docker-compose.yml` | 完整服务 (后端 + 前端)，使用预构建镜像 | 生产部署 |
| `docker-compose.build.yml` | 完整服务，本地构建镜像 | 本地开发全栈 |
| `docker-compose.infra.yml` | PostgreSQL + Redis，使用预构建镜像 | 本地开发仅基础设施 |
| `docker-compose.infra.build.yml` | PostgreSQL + Redis，本地构建镜像 | 本地开发仅基础设施（需自定义 postgres） |

## 容器日志配置

容器日志使用 json-file 驱动，自动轮转：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # 单文件最大 10MB
    max-file: "5"      # 最多 5 个文件
```

查看日志：

```bash
# 实时跟踪
docker compose -f docker/docker-compose.yml logs -f backend

# 最近 100 行
docker compose -f docker/docker-compose.yml logs --tail=100 backend

# 搜索错误
docker compose -f docker/docker-compose.yml logs backend | grep ERROR

# 跟踪特定请求
docker compose -f docker/docker-compose.yml logs -f backend | grep "request_id=abc123"
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `Dockerfile` | 后端 Python 镜像（含自动迁移） |
| `Dockerfile.frontend` | 前端 Node 镜像 |
| `Dockerfile.pg` | PostgreSQL + TimescaleDB 镜像（含初始化脚本） |
| `backend-entrypoint.sh` | 后端启动脚本（自动运行数据库迁移） |
| `init-db.sh` | PostgreSQL + TimescaleDB 初始化脚本 |
| `.env.docker` | Docker 环境配置模板 |

## 版本升级与迁移

后端容器启动时会**自动运行数据库迁移**（`alembic upgrade head`），确保每次版本升级都能自动应用最新的数据库 Schema 变更。

PostgreSQL 初始化脚本（`init-db.sh`）仅在数据库首次创建时执行，用于创建 TimescaleDB 扩展。如需重新初始化数据库，请先删除数据卷：

```bash
# 删除数据卷并重新创建（会丢失所有数据！）
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

## 环境变量

详细配置见 `.env.docker` 文件。关键配置项：

| 配置项 | 说明 | 必须修改 |
|--------|------|---------|
| `JWT_SECRET_KEY` | JWT 签名密钥 | **是** |
| `DB_PASSWORD` | 数据库密码 | 推荐修改 |
| `OPENAI_API_KEY` | OpenAI API Key | 可选 |

## 使用示例

```bash
# 生产部署（使用预构建镜像）
docker compose -f docker/docker-compose.yml up -d

# 生产部署（使用自定义配置）
docker compose -f docker/docker-compose.yml --env-file ./docker/.env.docker up -d

# 本地开发全栈（本地构建所有镜像）
docker compose -f docker/docker-compose.build.yml up -d --build

# 本地开发仅基础设施（使用预构建镜像）
docker compose -f docker/docker-compose.infra.yml up -d

# 本地开发仅基础设施（本地构建 postgres 镜像）
docker compose -f docker/docker-compose.infra.build.yml up -d --build

# 带管理工具 (pgAdmin, Redis Commander)
docker compose -f docker/docker-compose.yml --profile tools up -d

# 停止服务
docker compose -f docker/docker-compose.yml down

# 清理所有数据
docker compose -f docker/docker-compose.yml down -v
```

## 构建自定义镜像

```bash
# 构建 PostgreSQL 镜像（含初始化脚本）
docker build -t ghcr.io/cefso/sentinelx/postgres:latest -f Dockerfile.pg .

# 构建后端镜像
docker build -t ghcr.io/cefso/sentinelx/backend:latest -f Dockerfile ../backend

# 构建前端镜像
docker build -t ghcr.io/cefso/sentinelx/frontend:latest -f Dockerfile.frontend ../frontend
```
