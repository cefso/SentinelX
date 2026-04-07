# SentinelX - 综合告警平台

企业级、多租户、高可用的综合告警平台。

## 开发进度

- [x] Phase 1: 基础设施与核心框架 (完成)
- [x] Phase 2: 租户与告警核心功能 (完成)
- [x] Phase 3: 规则引擎与通知系统 (完成)
- [x] Phase 4: AI智能增强 (完成)
- [x] Phase 5: 运维闭环与Agent (完成)
- [x] Phase 6: 优化与上线 (完成)

## 特性

- **多租户管理**: 基于RBAC的租户隔离，支持资源配额控制，支持用户属于多个租户
- **多源告警接入**: 支持 Prometheus、Alertmanager、阿里云云监控（1.0/2.0）、腾讯云、Zabbix、自定义 Webhook 等，通过适配器自动解析各类告警格式
- **告警源管理**: 支持配置多个告警源（AlertSource），每个告警源有独立的 Webhook URL，支持启用/禁用和统计
- **告警聚合视图**: 告警列表支持按指纹（fingerprint）聚合模式，同一告警的多条记录合并展示并显示触发次数
- **智能规则引擎**: 基于标签的路由规则，支持 AND/OR 逻辑和正则匹配
- **告警处理**: 去重、抑制、聚合、升级策略
- **多渠道通知**: 钉钉、飞书、企业微信、邮件等
- **AI增强**: LLM接入，支持根因分析和内容润色
- **诊断模式**: Trace ID 全链路追踪
- **双认证**: JWT用户认证 + API Key服务认证
- **租户切换**: 用户可同时属于多个租户，支持前端快速切换
- **用户注册审批**: 用户注册需管理员审批通过后方可登录，支持多租户权限分配

## 技术栈

### 后端
- Python 3.11 + FastAPI
- PostgreSQL + TimescaleDB (时序扩展)
- Redis
- PGMQ (PostgreSQL 原生消息队列)
- SQLAlchemy + Pydantic + Alembic

### 前端
- React 18 + TypeScript
- Vite + shadcn/ui + Tailwind CSS
- Zustand + React Query

### 架构优势
- JSONB + GIN 索引：毫秒级动态查询
- CTE + 窗口函数：数据库层聚合/去重
- TimescaleDB：自动分区与降采样
- PGMQ：PostgreSQL 原生消息队列

## 快速开始

### 环境要求
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### 1. 克隆项目

```bash
cd /Users/cefso/code/SentinelX
```

### 2. 启动外部依赖

使用 Docker 启动 PostgreSQL 和 Redis：

```bash
docker compose -f docker/docker-compose.infra.yml up -d
```

这将启动:
- PostgreSQL (TimescaleDB + TimescaleDB 扩展) - 端口 5432
- Redis - 端口 6379

### 3. 本地开发 (前后端不使用 Docker)

**后端:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 运行迁移
alembic upgrade head

# 如果需要重置数据库
alembic downgrade base && alembic upgrade head

# 启动开发服务器
uvicorn main:app --host 0.0.0.0 --port 8001 --reload --log-level debug
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

### 4. 访问应用

- 前端: http://localhost:3000
- API 文档: http://localhost:8001/docs

### 5. 默认账号

应用首次启动时会自动创建默认租户和超级管理员账号：

| 类型 | 值 |
|------|------|
| 租户 Slug | `sentinelx` |
| 用户名 | `admin` |
| 密码 | `Admin@123456` |

> **注意**: 登录时使用 **用户名** `admin`，不是邮箱。

---

## Docker 部署

使用 Docker 运行完整服务（包括后端和前端）：

```bash
# 启动所有服务（后端、前端、PostgreSQL、Redis）
docker compose -f docker/docker-compose.yml up -d

# 启动带管理工具 (pgAdmin, Redis Commander)
docker compose -f docker/docker-compose.yml --profile tools up -d

# 本地构建镜像后启动
cd docker
docker compose up -d --build
```

管理工具地址:
- pgAdmin: http://localhost:5050
- Redis Commander: http://localhost:8081

## 文档

详细文档请参考 `docs/` 目录：

- [API 文档](docs/API.md) - 完整的 API 接口说明
- [部署指南](docs/DEPLOYMENT.md) - Docker Compose 和 Kubernetes 部署

## 项目结构

```
SentinelX/
├── backend/                    # Python后端
│   ├── apps/
│   │   ├── core/             # 核心模块（config/database/redis/mq/security/logging/middleware 等）
│   │   ├── auth/             # 认证授权
│   │   │   ├── api_key.py    # API Key认证
│   │   │   ├── dependencies.py # 依赖注入
│   │   │   ├── routers.py    # 认证路由
│   │   │   ├── schemas.py    # Pydantic Schema
│   │   │   └── services/     # 认证服务
│   │   ├── tenant/           # 租户管理
│   │   ├── alert/            # 告警核心
│   │   │   ├── adapters/     # 告警适配器（prometheus/aliyun/zabbix/tencent 等）
│   │   │   ├── models.py     # 数据模型
│   │   │   ├── routers.py    # API路由
│   │   │   ├── schemas.py    # Pydantic Schema
│   │   │   └── services/     # 业务逻辑
│   │   ├── rule/             # 规则引擎
│   │   │   ├── engine.py     # 规则匹配引擎
│   │   │   ├── models.py     # 规则数据模型
│   │   │   ├── routers.py    # 规则路由
│   │   │   ├── schemas.py    # Pydantic Schema
│   │   │   └── services/     # 规则服务
│   │   ├── notify/           # 通知系统
│   │   │   ├── channels/     # 通知渠道（钉钉/飞书/企微/邮件等）
│   │   │   ├── models.py     # 通知数据模型
│   │   │   ├── routers.py    # 通知路由
│   │   │   ├── schemas.py    # Pydantic Schema
│   │   │   ├── services/     # 通知服务
│   │   │   └── worker.py     # 通知队列worker
│   │   ├── ai/               # AI增强（根因分析/内容润色）
│   │   ├── escalation/        # 告警升级
│   │   ├── maintenance/      # 维护期管理
│   │   ├── callback/         # 回调处理
│   │   └── common/           # 共享常量/类型
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 单元测试
│   └── main.py               # 应用入口
├── frontend/                  # React前端
│   ├── src/
│   │   ├── pages/            # 页面组件（alerts/rules/channels/settings/admin/diagnose/login 等）
│   │   ├── components/        # 通用组件
│   │   │   └── condition/     # 条件选择组件（ConditionRow、constants 等）
│   │   ├── services/          # API服务
│   │   ├── stores/            # 状态管理（Zustand）
│   │   ├── hooks/            # React Hooks
│   │   ├── libs/             # 工具库
│   │   └── types/            # TypeScript 类型定义
│   └── package.json
├── agent/                     # 内网 Agent（Python）
├── docker/                    # Docker 配置
│   ├── docker-compose.yml    # 完整服务
│   ├── docker-compose.infra.yml # 基础设施
│   ├── Dockerfile             # 后端镜像
│   ├── Dockerfile.frontend   # 前端镜像
│   ├── Dockerfile.pg          # PostgreSQL + TimescaleDB 镜像
│   ├── backend-entrypoint.sh   # 后端启动脚本
│   ├── init-db.sh             # 数据库初始化脚本
│   ├── .env.docker            # Docker 环境配置
│   └── README.md              # Docker 详细说明
├── k8s/                       # Kubernetes 部署配置
│   ├── namespace.yaml         # 命名空间/ConfigMap/Secret
│   ├── postgres-deployment.yaml # PostgreSQL
│   ├── redis-deployment.yaml   # Redis
│   ├── backend-deployment.yaml # 后端
│   ├── frontend-deployment.yaml # 前端+Ingress
│   ├── backend-hpa.yaml       # 后端自动扩缩容
│   └── frontend-hpa.yaml     # 前端自动扩缩容
├── docs/                      # 详细文档
│   ├── API.md                 # API 文档
│   ├── DEPLOYMENT.md          # 部署指南
│   └── README.md              # 文档目录说明
├── .github/workflows/          # CI/CD配置
│   ├── ci.yml                # 持续集成
│   └── cd.yml                # 持续部署
└── README.md
```

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         接入层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Prometheus│  │ Alertmanager│ │ 云监控    │  │  Webhook API    │ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────────┬─────────┘ │
│        └──────────────┴──────────────┴─────────────────┘          │
│                              │                                    │
│                    ┌─────────▼─────────┐                         │
│                    │   告警接收 API     │                         │
│                    │  (统一接入网关)     │                         │
│                    └─────────┬─────────┘                         │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        核心处理层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ 适配器    │  │ 规则引擎  │  │ 去重/聚合 │  │   AI 增强模块   │ │
│  └─────┬────┘  └─────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│        │            │             │                  │            │
│        └────────────┴─────────────┴──────────────────┘            │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      PostgreSQL + Redis                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐│
│  │   JSONB/GIN 存储 │  │  Redis 缓存     │  │  结构化日志     ││
│  └──────────────────┘  └──────────────────┘  └──────────────────┘│
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                         通知层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ 钉钉     │  │ 飞书      │  │ 企业微信  │  │   邮件/Webhook  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 告警处理流程

```
告警接入 → 指纹生成 → 去重检查(5分钟窗口) → 抑制检查(维护期) →
聚合检查(告警列表聚合视图) → 规则匹配(AND/OR条件) → 通知队列 → 多渠道发送
```

## 核心概念
```
接入 → 指纹生成 → 去重检查 → 抑制检查 → 聚合检查（可选，API 层面）→ 规则匹配 → 通知发送
```

### 多租户架构

SentinelX 支持用户属于多个租户，通过 UserTenant 关联表实现 N:M 关系：

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │       │  UserTenant  │       │   Tenant    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id          │───1:N──│ user_id     │───N:1──│ id          │
│ username    │       │ tenant_id    │       │ name        │
│ email       │       │ role_id     │───N:1──│ slug        │
│ is_system   │       │ is_current  │       │ is_active   │
│ is_approved │       │ is_primary  │       │ is_active   │
│ is_active   │       └─────────────┘       └─────────────┘
└─────────────┘
```

- **is_system**: 系统管理员标志，拥有全局权限
- **is_superuser**: 租户管理员标志，在当前租户内有全部权限
- **is_approved**: 用户注册审批状态，注册后需管理员审批
- **is_active**: 用户账号启用/禁用状态
- **is_current**: 用户当前活跃的租户
- **is_primary**: 用户的主租户
- **scope**: 角色范围，system 或 tenant

### 用户注册与审批流程

```
用户注册 → 待审批状态 → 系统管理员审批 → 分配角色/租户 → 正常登录
                              ↓
                         审批拒绝 → 账号无效
```

- 新用户注册后 `is_approved=False`，无法登录
- 系统管理员在 `/admin/users` 审批用户
- 审批通过后可分配系统级角色或租户角色
- 租户管理员可管理本租户内的用户

### 认证体系

| 认证方式 | 用途 | Header |
|----------|------|--------|
| JWT Bearer Token | 用户登录 | `Authorization: Bearer xxx` |
| API Key | Agent/服务 | `X-API-Key: sxk_v1_xxx` |

### Trace ID 诊断
每条告警都有唯一的 12 位 Trace ID，可用于诊断告警处理全流程。

## 配置说明

### 环境变量

```env
# 应用配置
APP_NAME=SentinelX
DEBUG=true

# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=sentinelx

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT (生产环境必须修改)
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI (可选)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
DASHSCOPE_API_KEY=sk-xxx
AI_MODEL=gpt-4
AI_PROVIDER=openai

# 日志配置
LOG_LEVEL=INFO              # DEBUG/INFO/WARNING/ERROR
LOG_FORMAT=json            # json/console
LOG_FILE=                   # 日志文件路径（可选，留空输出到stdout）

# PGMQ (PostgreSQL消息队列)
PGMQ_ENABLED=true
```

## 日志配置

### 后端日志级别

| 环境变量 | 说明 | 默认值 | 可选值 |
|----------|------|--------|--------|
| `LOG_LEVEL` | 日志级别 | INFO | DEBUG/INFO/WARNING/ERROR |
| `LOG_FORMAT` | 日志格式 | json | json/console |
| `LOG_FILE` | 日志文件路径 | - | 绝对路径（可选） |

### 日志格式

**JSON 格式（生产环境）**:
```json
{
  "event": "request_completed",
  "timestamp": "2024-01-01T10:00:00.000Z",
  "level": "info",
  "service": "sentinelx",
  "request_id": "abc123",
  "method": "POST",
  "path": "/api/v1/alerts",
  "status_code": 200,
  "duration_ms": 45.23
}
```

**控制台格式（开发环境）**:
```
2024-01-01T10:00:00.000Z [apps.alert.routers] INFO: request_completed
  method=POST
  path=/api/v1/alerts
  status_code=200
  duration_ms=45.23
```

### 前端日志

| 环境变量 | 说明 | 默认值 | 可选值 |
|----------|------|--------|--------|
| `VITE_LOG_LEVEL` | 日志级别 | info | debug/info/warn/error |
| `VITE_ENABLE_LOGGING` | 是否启用日志 | true | true/false |

### Docker 日志

容器日志使用 json-file 驱动，自动轮转:

查看容器日志:
```bash
# 查看所有日志
docker compose -f docker/docker-compose.yml logs -f

# 查看后端日志
docker compose -f docker/docker-compose.yml logs -f backend

# 查看最近 100 行
docker compose -f docker/docker-compose.yml logs --tail=100 backend
```

### 请求追踪

每个请求带有 `X-Request-ID` 响应头，用于关联日志:
```bash
curl -v http://localhost:8001/api/v1/alerts 2>&1 | grep -i x-request-id
```

## API 文档

启动服务后访问 http://localhost:8001/docs 查看完整的 OpenAPI 文档。

### 认证
```
POST /api/v1/auth/login          # 用户登录
POST /api/v1/auth/register       # 用户注册（需管理员审批）
POST /api/v1/auth/refresh        # 刷新Token
POST /api/v1/auth/switch-tenant # 切换租户
GET  /api/v1/auth/tenants        # 获取我的租户列表
GET  /api/v1/auth/me             # 当前用户信息
GET  /api/v1/auth/permissions    # 获取我的权限
POST /api/v1/auth/api-keys       # 创建API Key
GET  /api/v1/auth/api-keys       # 列出API Key
DELETE /api/v1/auth/api-keys/{key_id}  # 撤销API Key
```

### 租户管理
```
GET    /api/v1/tenants           # 获取租户列表
POST   /api/v1/tenants           # 创建租户
GET    /api/v1/tenants/current   # 获取当前租户
GET    /api/v1/tenants/{id}      # 获取租户详情
PUT    /api/v1/tenants/{id}      # 更新租户
GET    /api/v1/tenants/public    # 获取公开租户列表（注册时使用）
GET    /api/v1/tenants/{id}/webhook-key     # 获取Webhook Key
POST   /api/v1/tenants/{id}/webhook-key     # 生成/重置Webhook Key
GET    /api/v1/roles             # 获取角色列表
POST   /api/v1/roles             # 创建角色
```

### 告警源管理
```
GET    /api/v1/alerts/sources             # 获取告警源列表
POST   /api/v1/alerts/sources             # 创建告警源（需传入 client_id）
GET    /api/v1/alerts/sources/stats        # 获取各告警源的统计数据（总数/触发中数）
```

**告警源 client_id**: 客户端生成的随机短ID（如 8 位十六进制），用于构造 Webhook URL，比内部 ID 更安全且无需泄露数据库主键。

### Webhook（多租户）
```
POST   /api/v1/webhooks/{tenant_slug}/{source_type}/{client_id}  # 接收告警（多租户版本，支持告警源）
GET    /api/v1/tenants/{id}/webhook-key              # 获取 Webhook URL 信息
POST   /api/v1/tenants/{id}/webhook-key              # 生成/重置 Webhook API Key
```

**多租户 Webhook URL 结构:**
```
/api/v1/webhooks/{tenant_slug}/prometheus/{client_id}
/api/v1/webhooks/{tenant_slug}/alertmanager/{client_id}
/api/v1/webhooks/{tenant_slug}/grafana/{client_id}
/api/v1/webhooks/{tenant_slug}/aliyun/{client_id}
/api/v1/webhooks/{tenant_slug}/aliyun_cms/{client_id}   # 阿里云云监控1.0
/api/v1/webhooks/{tenant_slug}/aliyun_cms2/{client_id} # 阿里云云监控2.0
/api/v1/webhooks/{tenant_slug}/tencent/{client_id}
/api/v1/webhooks/{tenant_slug}/zabbix/{client_id}
/api/v1/webhooks/{tenant_slug}/custom/{client_id}
```

- **tenant_slug**: 租户标识（如 `sentinelx`）
- **source_type**: 告警源类型（见上）
- **client_id**: 告警源客户端ID（在告警源管理中创建后获得，支持数字 ID 或 client_id）

**认证方式:** 通过 `X-API-Key` Header 传递 Webhook API Key

### 用户管理
```
GET    /api/v1/users                       # 获取用户列表（租户管理员）
POST   /api/v1/users                       # 创建用户（租户管理员）
GET    /api/v1/users/{id}                   # 获取用户详情
PUT    /api/v1/users/{id}                   # 更新用户
PUT    /api/v1/users/{id}/password          # 修改密码
PUT    /api/v1/users/{id}/role             # 更新用户角色
DELETE /api/v1/users/{id}                   # 从租户移除用户
POST   /api/v1/users/{id}/activate          # 激活/禁用用户
```

### 系统管理员 - 用户审批
```
GET    /api/v1/admin/users/pending         # 获取待审批用户列表
POST   /api/v1/admin/users/{user_id}/approve   # 审批通过用户
POST   /api/v1/admin/users/{user_id}/reject     # 拒绝用户注册
```

### 告警
```
POST   /api/v1/alerts             # 接收告警
POST   /api/v1/alerts/batch       # 批量接收告警
POST   /api/v1/alerts/webhook/{source_type}  # Webhook接收告警
GET    /api/v1/alerts             # 告警列表（支持 aggregate=true 聚合模式）
GET    /api/v1/alerts/stats        # 告警统计
GET    /api/v1/alerts/{id}         # 告警详情
PUT    /api/v1/alerts/{id}        # 更新告警
GET    /api/v1/alerts/{id}/aggregated-members  # 获取聚合组的告警列表
GET    /api/v1/alerts/diagnose/{trace_id}  # 诊断
```

**告警列表聚合模式**: 使用 `GET /api/v1/alerts?aggregate=true` 可按指纹（fingerprint）聚合，同一告警的多条记录合并展示，返回 `count`（触发次数）和 `latest`（最新告警）。

### 云产品指标映射
```
GET    /api/v1/cloud-metrics              # 获取云产品指标列表
GET    /api/v1/cloud-metrics/map?namespace=acs_ecs  # 获取指定namespace的指标详情
```

**cloud_product_metrics 表**: 存储云产品 namespace 与中文名称的映射关系，支持通过数据库直接维护。

| 字段 | 说明 | 示例 |
|------|------|------|
| namespace | 产品命名空间 | acs_ecs, acs_rds, acs_slb |
| product | 产品中文名称 | 阿里云ECS, 阿里云RDS |
| metric_name | 指标名称 | CPUUtilization |
| metric_desc | 指标中文描述 | CPU使用率 |

**告警新字段**: alerts 表新增 `namespace`、`instance_id`、`instance_name` 字段，用于存储云产品关键信息，列表页和详情页直接展示。

### 规则
```
GET    /api/v1/rules              # 规则列表
POST   /api/v1/rules              # 创建规则
GET    /api/v1/rules/{id}         # 规则详情
PUT    /api/v1/rules/{id}        # 更新规则
DELETE /api/v1/rules/{id}        # 删除规则
POST   /api/v1/rules/test        # 测试规则
POST   /api/v1/rules/preview-dedup      # 预览去重匹配告警
POST   /api/v1/rules/preview-aggregate   # 预览聚合匹配告警
GET    /api/v1/rules/field-values       # 获取规则字段的可选值（用于下拉提示）
```

**规则预览 API**:

`POST /api/v1/rules/preview-dedup` - 预览去重配置匹配的告警
```json
{
  "deduplication_config": {
    "dedup_type": "condition",
    "window_seconds": 300,
    "conditions": [{"field": "source", "operator": "eq", "value": "prometheus"}],
    "condition_mode": "and"
  },
  "status": "firing",
  "severity": "critical",
  "source": "prometheus"
}
```

`POST /api/v1/rules/preview-aggregate` - 预览聚合配置匹配的告警
```json
{
  "aggregate_config": {
    "mode": "condition",
    "window_seconds": 300,
    "conditions": [{"field": "namespace", "operator": "eq", "value": "prod"}],
    "condition_mode": "and"
  },
  "status": "firing",
  "severity": "critical",
  "source": "prometheus"
}
```

响应格式：
```json
{
  "items": [...],  // 告警列表（去重）或聚合组列表（聚合）
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

**字段值获取 API**:

`GET /api/v1/rules/field-values?field=severity&search=&limit=50` - 获取规则条件字段的可选值

| 参数 | 说明 |
|------|------|
| field | 字段名（severity/source/status/assignee/namespace/instance_id/alert_key/metric_name/labels.{key}） |
| search | 搜索关键字（可选） |
| limit | 返回数量限制（默认50） |

响应格式：
```json
{
  "values": [
    {"value": "critical", "count": 10},
    {"value": "high", "count": 5}
  ]
}
```

### 通知渠道
```
GET    /api/v1/channel-types      # 获取支持的渠道类型列表
GET    /api/v1/channels           # 渠道列表
POST   /api/v1/channels           # 创建渠道
GET    /api/v1/channels/{id}      # 渠道详情
PUT    /api/v1/channels/{id}      # 更新渠道
DELETE /api/v1/channels/{id}      # 删除渠道
POST   /api/v1/channels/{id}/test # 测试渠道配置
GET    /api/v1/notifications       # 通知发送历史
```

### 通知模板
```
GET    /api/v1/templates           # 模板列表
POST   /api/v1/templates           # 创建模板
GET    /api/v1/templates/{id}      # 模板详情
PUT    /api/v1/templates/{id}      # 更新模板
DELETE /api/v1/templates/{id}      # 删除模板
```

### 健康检查
```
GET /health          # 健康检查
GET /health/ready   # 就绪探针 (检查数据库/Redis)
GET /health/live    # 存活探针
```

### 告警升级
```
GET    /api/v1/alerts/escalation/candidates  # 获取可升级的告警列表
POST   /api/v1/alerts/{id}/escalate         # 手动升级告警
POST   /api/v1/alerts/escalation/check      # 检查告警是否需要升级
```

### 维护窗口
```
GET    /api/v1/maintenance/windows           # 获取维护窗口列表
POST   /api/v1/maintenance/windows           # 创建维护窗口
GET    /api/v1/maintenance/windows/{id}     # 获取维护窗口详情
PUT    /api/v1/maintenance/windows/{id}     # 更新维护窗口
DELETE /api/v1/maintenance/windows/{id}     # 删除维护窗口
GET    /api/v1/maintenance/windows/{id}/check # 检查告警是否在维护窗口内
```

## 开发指南

### 添加新的告警源适配器

1. 在 `backend/apps/alert/adapters/` 创建适配器类（如 `aliyun_cms.py`）
2. 继承 `AlertAdapter` 基类
3. 实现 `parse()` 方法
4. 在 `AdapterFactory._adapters` 注册适配器

```python
class PrometheusAdapter(AlertAdapter):
    async def parse(self, raw_data: dict, tenant_id: str) -> AlertCreate:
        # 实现解析逻辑
        return AlertCreate(...)
```

### 阿里云云监控1.0适配器

阿里云云监控1.0适配器（`aliyun_cms.py`）处理阿里云云监控的告警格式，关键字段说明：

**原始数据字段**:
- `alertState`: 告警状态
  - `OK` - 正常（恢复），会触发恢复逻辑
  - `ALERT` - 报警（触发）
  - `INSUFFICIENT_DATA` - 无数据
- `triggerLevel`: 本次触发报警的级别
  - `CRITICAL` - 严重
  - `WARN` - 警告
  - `INFO` - 信息
- `alertName`: 告警名称
- `rawMetricName`: 原始指标名
- `metricName`: 指标名
- `expression`: 触发表达式
- `lastTime`: 持续时间

**告警键生成**:
```
alert_key = aliyun_cms-{alertName}-{rawMetricName}-{instance_id}
```
注意：`lastTime` 不包含在 alert_key 中，避免同一告警因持续时间变化导致指纹不同。

**严重等级映射**:
| triggerLevel | severity |
|-------------|----------|
| CRITICAL | critical |
| WARN | high |
| INFO | info |

**恢复处理**:
当 `alertState=OK`（或等效的恢复状态）时，系统会：
1. 通过 fingerprint 查找同指纹的 firing 状态告警，标记为 resolved
2. 创建 AlertHistory 记录状态变化（action="resolved"）
3. 创建新的告警记录（status=resolved），每条消息都忠实记录

支持恢复处理的适配器：
- **aliyun_cms**: `alertState=OK`
- **aliyun_cms2**: `state=OK` 或 `state=RESOLVED`
- **prometheus/alertmanager**: `status=resolved`

**INSUFFICIENT_DATA 处理**:
当 `alertState=INSUFFICIENT_DATA` 时，系统会：
- 将 severity 降级为 low
- 继续正常告警创建流程

**指纹一致性**:
恢复消息（OK）的 fingerprint 与触发消息相同，因为 fingerprint 计算使用的是 labels（不含 severity 字段）。

**忠实记录原则**:
所有适配器（aliyun_cms、aliyun_cms2、prometheus、zabbix、tencent、custom 等）都遵循忠实记录原则：
- 每条告警消息都会创建独立的 Alert 记录
- 不进行去重，重复消息继续通过完整处理流程
- 每条记录的 fire_count = 1

**通知去重**:
虽然存储层忠实记录每条消息，但通知发送层会进行去重：
- 使用 fingerprint 作为去重键
- 去重窗口：5分钟（300秒）
- 同一 fingerprint 在窗口期内只发送一次通知
- OK 恢复消息不发送通知

### 添加新的通知渠道

1. 在 `backend/apps/notify/channels/` 创建渠道类
2. 继承 `NotificationChannel` 基类
3. 实现 `send()` 方法

```python
class DingTalkChannel(NotificationChannel):
    async def send(self, alert: Alert, template: Template) -> bool:
        # 实现发送逻辑
        return True
```

## 测试

```bash
# 运行所有测试
cd backend
pytest tests/ -v

# 运行带覆盖率的测试
pytest tests/ -v --cov=apps --cov-report=html
```

## CI/CD

GitHub Actions 自动处理:
- 后端单元测试
- 前端构建测试
- Docker 镜像构建
- 数据库迁移验证

推送代码后自动触发CI流程。

## 故障排查

### 常见问题

#### 1. 登录失败，提示 "Invalid credentials"
- 检查默认账号: 用户名 `admin`，密码 `Admin@123456`
- 检查数据库是否正确初始化: `alembic upgrade head`
- 检查 Redis 是否运行: `docker compose -f docker/docker-compose.yml ps redis`

#### 2. 告警未收到通知
- 检查规则是否正确配置
- 检查通知渠道是否启用
- 查看后端日志: `docker compose -f docker/docker-compose.yml logs -f backend | grep notification`

#### 3. 性能问题
- 检查数据库索引是否创建
- 检查 Redis 连接数
- 查看慢请求日志: 设置 `LOG_LEVEL=DEBUG`

#### 4. Docker 容器无法启动
- 检查端口占用: `lsof -i :8001` 或 `lsof -i :3000`
- 检查日志: `docker compose -f docker/docker-compose.yml logs`
- 清理重建: `docker compose -f docker/docker-compose.yml down && docker compose -f docker/docker-compose.yml up -d`

#### 5. 前端无法连接后端
- 检查 API 代理配置: `VITE_API_PROXY_TARGET`
- 检查后端 CORS 配置: `DEBUG=true`
- 查看浏览器控制台日志

### 日志分析

#### 查看错误日志
```bash
# 本地开发
cd backend
grep -i error logs/*.log

# Docker 环境
docker compose -f docker/docker-compose.yml logs backend | grep -i error
```

#### 追踪请求
每个请求带有 `X-Request-ID` 响应头，用于关联日志:
```bash
curl -v http://localhost:8001/api/v1/alerts 2>&1 | grep -i x-request-id
```

#### 审计日志
审计日志记录在 `audit_logs` 表中，可通过 API 查询敏感操作记录。

### 获取帮助

- 查看 API 文档: http://localhost:8001/docs
- 查看前端控制台日志
- 查看后端日志追踪请求

## 许可证

MIT License
