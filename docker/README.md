# SentinelX 综合告警平台

企业级、多租户、高可用的综合告警平台。支持多数据源接入、智能路由、多通道通知、交互闭环以及 AI 增强能力。

---

## Docker 部署架构

本项目采用前后端分离的 Docker 部署方式：

| 文件 | 说明 | 使用场景 |
|------|------|---------|
| `docker-compose.infra.yml` | PostgreSQL + Redis | 本地开发、生产基础设施 |
| `docker-compose.yml` | 完整服务 (后端 + 前端) | Docker 完整部署 |

---

## 快速启动

### 方式一: 本地开发 (推荐)

前后端在本地运行，仅使用 Docker 启动基础设施：

```bash
# 1. 启动 PostgreSQL 和 Redis
docker-compose -f docker-compose.infra.yml up -d

# 2. 本地运行后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8001 --reload --log-level debug

# 3. 本地运行前端 (新开终端)
cd frontend
npm install
npm run dev
```

### 方式二: Docker 完整部署

所有服务都使用 Docker 运行：

```bash
docker-compose up -d
```

带管理工具:
```bash
docker-compose --profile tools up -d
```

### 访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3000 | React SPA 应用 |
| 后端 API | http://localhost:8001 | FastAPI REST API |
| API 文档 | http://localhost:8001/docs | Swagger UI |
| pgAdmin | http://localhost:5050 | 可选 - 数据库管理 |
| Redis Commander | http://localhost:8081 | 可选 - Redis 管理 |

### 4. 默认账号

应用首次启动时会自动创建默认租户和超级管理员账号：

| 类型 | 值 |
|------|------|
| 租户 Slug | `sentinelx` |
| 用户名 | `admin` |
| 密码 | `Admin@123456` |

> **注意**: 登录时使用 **用户名** `admin`，不是邮箱。

---

## 配置说明

### Docker 环境配置

Docker 环境配置位于 `docker/.env.docker`，可修改以下配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DB_HOST` | 数据库主机 | postgres |
| `DB_PORT` | 数据库端口 | 5432 |
| `DB_USER` | 数据库用户名 | postgres |
| `DB_PASSWORD` | 数据库密码 | postgres |
| `DB_NAME` | 数据库名 | sentinelx |
| `REDIS_HOST` | Redis 主机 | redis |
| `REDIS_PORT` | Redis 端口 | 6379 |
| `JWT_SECRET_KEY` | JWT 密钥 | (需修改) |
| `DEBUG` | 调试模式 | true |
| `OPENAI_API_KEY` | OpenAI API Key | (可选) |

使用自定义配置启动：

```bash
docker-compose --env-file ./docker/.env.docker up -d
```

### 后端环境配置

后端配置位于项目根目录 `.env.example`，复制为 `.env` 后修改：

```bash
cp .env.example .env
```

### 前端环境配置

前端配置位于 `frontend/.env.example`，复制为 `.env.local` 后修改：

```bash
cd frontend
cp .env.example .env.local
```

### 容器日志配置

容器日志使用 json-file 驱动，自动轮转:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # 单文件最大 10MB
    max-file: "5"     # 最多 5 个文件
```

查看日志:

```bash
# 实时跟踪
docker-compose logs -f backend

# 最近 100 行
docker-compose logs --tail=100 backend

# 搜索错误
docker-compose logs backend | grep ERROR

# 跟踪特定请求
docker-compose logs -f backend | grep "request_id=abc123"
```

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         接入层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Prometheus│  │ Alertmanager│ │ 云监控    │  │  Webhook API    │ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────────┬─────────┘ │
│        │              │              │                 │          │
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

---

## 模块说明

### 后端模块 (backend/apps)

| 模块 | 路径 | 说明 |
|------|------|------|
| **core** | apps/core/ | 核心模块：配置、数据库、Redis、日志、中间件、异常处理 |
| **auth** | apps/auth/ | 认证授权：JWT、API Key、RBAC 权限控制 |
| **tenant** | apps/tenant/ | 多租户管理：租户、用户、角色、团队 |
| **alert** | apps/alert/ | 告警核心：接入、分发、去重、聚合、抑制、状态机 |
| **rule** | apps/rule/ | 规则引擎：条件表达式、规则匹配、路由 |
| **notify** | apps/notify/ | 通知系统：渠道管理、模板、发送调度 |
| **ai** | apps/ai/ | AI 增强：根因分析、内容润色、LLM 集成 |
| **callback** | apps/callback/ | 回调处理：告警确认、处理、恢复 |
| **escalation** | apps/escalation/ | 升级策略：未确认告警自动升级 |

### 前端模块 (frontend/src)

| 目录 | 说明 |
|------|------|
| pages/ | 页面：告警列表、规则管理、渠道配置、AI 设置等 |
| components/ | 组件：布局、UI 组件、业务组件 |
| services/ | API 服务封装 |
| stores/ | Zustand 状态管理 |
| hooks/ | 自定义 React Hooks |

---

## 数据库设计

### 核心表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `tenants` | 租户表 | id, name, slug, config, max_alerts, max_users, max_rules |
| `users` | 用户表 | id, tenant_id, username, email, password_hash, is_superuser |
| `roles` | 角色表 | id, tenant_id, name, code, permissions (JSON) |
| `user_roles` | 用户角色关联 | user_id, role_id |
| `teams` | 团队表 | id, tenant_id, name, leader_id |
| `user_teams` | 用户团队关联 | user_id, team_id |
| `alert_sources` | 告警源配置 | id, tenant_id, name, code, source_type, config |
| `alerts` | 告警实例表 | id, tenant_id, fingerprint, severity, status, labels (JSONB) |
| `alert_history` | 告警历史 | alert_id, action, operator_id, old_value, new_value |
| `alert_traces` | 告警追踪 | trace_id, final_status, steps_chain (JSONB) |
| `alert_rules` | 告警规则 | id, tenant_id, conditions (JSON), condition_mode, actions |
| `notification_channels` | 通知渠道 | id, tenant_id, name, channel_type, config |
| `notification_templates` | 通知模板 | id, tenant_id, channel_type, content (Jinja2) |
| `notification_records` | 通知记录 | id, alert_id, channel_id, status, retry_count |
| `audit_logs` | 审计日志 | tenant_id, user_id, action, resource_type, details |

### JSONB + GIN 索引

利用 JSONB 字段存储动态数据，GIN 索引保证毫秒级查询：

```python
# alerts 表 labels 字段示例
{
  "cluster": "prod-k8s",
  "env": "production",
  "region": "us-east-1",
  "service": "payment-api"
}

# 告警规则 conditions 字段示例
[
  {"field": "severity", "operator": "in", "value": ["critical", "high"]},
  {"field": "labels.cluster", "operator": "eq", "value": "prod"}
]
```

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | 0.111.0 | Web 框架 |
| **Uvicorn** | 0.29.0 | ASGI 服务器 |
| **SQLAlchemy** | 2.0.30 | ORM (异步) |
| **asyncpg** | 0.29.0 | PostgreSQL 异步驱动 |
| **Alembic** | 1.13.1 | 数据库迁移 |
| **Redis** | 5.0.4 | 缓存、去重、消息队列 |
| **Pydantic** | 2.7.1 | 数据验证 |
| **python-jose** | 3.3.0 | JWT 认证 |
| **passlib** | 1.7.4 | 密码加密 |
| **structlog** | 24.1.0 | 结构化日志 |
| **httpx** | 0.27.0 | HTTP 客户端 |
| **Jinja2** | 3.1.4 | 通知模板引擎 |
| **anthropic** | 0.25.0 | Claude AI |
| **openai** | 1.30.1 | GPT AI |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18.x | UI 框架 |
| **TypeScript** | 5.x | 类型系统 |
| **Vite** | 5.x | 构建工具 |
| **shadcn/ui** | - | UI 组件库 |
| **Tailwind CSS** | 3.x | 样式框架 |
| **Zustand** | 4.x | 状态管理 |
| **React Router** | 6.x | 路由 |
| **TanStack Query** | 5.x | 数据请求 |

### 基础设施

| 技术 | 说明 |
|------|------|
| **PostgreSQL 16** | 主数据库 |
| **TimescaleDB** | 时序扩展 (可选) |
| **Redis 7** | 缓存和消息队列 |
| **Docker** | 容器化 |
| **Kubernetes** | 生产部署 |

---

## 关键功能实现

### 1. 告警指纹去重

```python
# 基于 source + metric_name + labels 生成唯一指纹
def generate_fingerprint(alert: AlertCreate) -> str:
    fp_data = {
        "source": alert.source,
        "metric_name": alert.metric_name,
        "labels": json.dumps(alert.labels, sort_keys=True)
    }
    return hashlib.sha256(json.dumps(fp_data, sort_keys=True).encode()).hexdigest()[:16]
```

Redis SET NX 实现原子性去重检查：

```python
dedup_key = f"dedup:{tenant_id}:{fingerprint}"
is_new = await redis.set(dedup_key, alert_id, nx=True, ex=300)  # 5分钟窗口
```

### 2. 规则引擎

支持 AND/OR 条件组合，条件操作符：

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `eq` | 等于 | severity eq "critical" |
| `ne` | 不等于 | status ne "resolved" |
| `gt/gte/lt/lte` | 比较 | metric_value > 100 |
| `in` | 包含 | severity in ["critical", "high"] |
| `contains` | 字符串包含 | title contains "CPU" |
| `regex` | 正则匹配 | labels.cluster regex "^prod-.*" |

```python
# 规则条件示例
conditions = [
    {"field": "severity", "operator": "in", "value": ["critical", "high"]},
    {"field": "labels.cluster", "operator": "eq", "value": "prod"}
]
condition_mode = "and"
```

### 3. 告警追踪 (Trace ID)

每条告警从接入到发送的完整生命周期都被记录，支持 Trace ID 诊断：

```python
# 处理流程
RECEIVED → DEDUP_CHECK → SUPPRESS_CHECK → AGGREGATE_CHECK → RULE_MATCH → NOTIFICATION_QUEUED

# 追踪数据结构
{
    "trace_id": "a1b2c3d4e5f6",
    "alert_id": "12345",
    "final_status": "sent|suppressed|duplicate|failed",
    "steps_chain": [
        {"type": "received", "time": "2024-01-01T10:00:00Z", "status": "success"},
        {"type": "dedup_check", "time": "2024-01-01T10:00:01Z", "status": "passed"}
    ]
}
```

### 4. 通知模板 (Jinja2)

```jinja2
{{#if severity == "critical"}}🔥{{else if severity == "high"}}🔴{{else}}🟡{{/if}}
[{{severity|upper}}] {{title}}

来源: {{source}}
时间: {{fired_at}}
{{#if metric_value}}指标值: {{metric_value}}{{/if}}
{{#if ai_root_cause}}
---
🤖 AI 分析: {{ai_root_cause}}
{{/if}}
```

### 5. 多租户隔离

- 租户间数据完全隔离 (tenant_id 过滤)
- JWT Token 包含 tenant_id
- RBAC 权限控制到租户级别
- API Key 绑定租户

---

## API 路由

| 前缀 | 模块 | 说明 |
|------|------|------|
| `/api/v1/auth` | 认证 | 登录、注册、Token 刷新 |
| `/api/v1/tenants` | 租户管理 | 租户 CRUD、用户管理、角色管理 |
| `/api/v1/alerts` | 告警 | 告警列表、详情、确认、恢复、静默 |
| `/api/v1/rules` | 规则 | 规则 CRUD、条件配置 |
| `/api/v1/channels` | 渠道 | 渠道 CRUD、测试发送 |
| `/api/v1/templates` | 模板 | 模板 CRUD |
| `/api/v1/ai` | AI | 根因分析、内容润色 |
| `/api/v1/callback` | 回调 | 外部系统回调 |

---

## 服务端口

| 服务 | 端口 | 环境变量 | 说明 |
|------|------|----------|------|
| PostgreSQL | 5432 | DB_HOST, DB_PORT | sentinelx / postgres |
| Redis | 6379 | REDIS_HOST, REDIS_PORT | - |
| Backend API | 8000 | PORT | 生产端口 |
| Backend API | 8001 | - | Docker 映射端口 |
| Frontend | 3000 | VITE_API_BASE_URL | React 开发服务器 |
| pgAdmin | 5050 | - | 可选工具 |
| Redis Commander | 8081 | - | 可选工具 |

---

## 常用命令

```bash
# ============================================================================
# 基础设施命令 (PostgreSQL + Redis)
# ============================================================================

# 启动基础设施
docker-compose -f docker-compose.infra.yml up -d

# 查看基础设施状态
docker-compose -f docker-compose.infra.yml ps

# 查看基础设施日志
docker-compose -f docker-compose.infra.yml logs -f

# 停止基础设施
docker-compose -f docker-compose.infra.yml down

# 清理基础设施数据
docker-compose -f docker-compose.infra.yml down -v

# ============================================================================
# 完整服务命令 (后端 + 前端)
# ============================================================================

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启服务
docker-compose restart backend

# 进入容器
docker exec -it sentinelx-backend bash
docker exec -it sentinelx-postgres psql -U postgres -d sentinelx

# 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 停止服务
docker-compose down

# 清理数据 (删除所有数据)
docker-compose down -v
```

---

## 目录结构

```
SentinelX/
├── backend/                          # Python 后端
│   ├── apps/                         # 应用模块
│   │   ├── core/                     # 核心模块
│   │   ├── auth/                     # 认证授权
│   │   ├── tenant/                   # 多租户管理
│   │   ├── alert/                    # 告警核心
│   │   │   ├── services/             # 服务层
│   │   │   │   ├── dispatcher.py     # 分发器
│   │   │   │   └── tracer.py         # 追踪器
│   │   │   └── adapters/             # 数据适配器
│   │   ├── rule/                     # 规则引擎
│   │   ├── notify/                   # 通知系统
│   │   │   └── channels/             # 通知渠道
│   │   └── ai/                       # AI 增强
│   ├── alembic/                      # 数据库迁移
│   │   └── versions/                 # 迁移版本
│   ├── main.py                       # FastAPI 入口
│   └── requirements.txt
│
├── frontend/                         # React 前端
│   ├── src/
│   │   ├── components/               # 组件
│   │   ├── pages/                    # 页面
│   │   ├── services/                 # API 服务
│   │   ├── stores/                   # 状态管理
│   │   └── App.tsx
│   └── package.json
│
├── docker/                           # Docker 配置
│   ├── docker-compose.yml           # 完整服务 (后端 + 前端)
│   ├── docker-compose.infra.yml     # 基础设施 (PG + Redis)
│   ├── Dockerfile
│   ├── Dockerfile.frontend
│   ├── init-db.sh
│   ├── .env.docker
│   └── README.md
│
├── agent/                            # 内网 Agent
├── k8s/                              # Kubernetes 部署
└── README.md
```
