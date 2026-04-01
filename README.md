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
- **多源告警接入**: 支持 Prometheus、Alertmanager、阿里云、腾讯云、华为云、Zabbix、Grafana 等
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
docker-compose -f docker/docker-compose.infra.yml up -d
```

这将启动:
- PostgreSQL (TimescaleDB) - 端口 5432
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

## Docker 部署 (可选)

如需使用 Docker 运行完整服务（包括后端和前端）：

```bash
# 启动基础设施 + 后端 + 前端
docker-compose -f docker/docker-compose.yml up -d

# 启动带管理工具 (pgAdmin, Redis Commander)
docker-compose --profile tools up -d
```

管理工具地址:
- pgAdmin: http://localhost:5050
- Redis Commander: http://localhost:8081

## 项目结构

```
SentinelX/
├── backend/                    # Python后端
│   ├── apps/
│   │   ├── core/             # 核心模块
│   │   │   ├── config.py     # 配置管理
│   │   │   ├── database.py   # 数据库连接
│   │   │   ├── redis.py      # Redis连接
│   │   │   ├── mq.py         # PGMQ消息队列
│   │   │   ├── security.py   # JWT/AES加密
│   │   │   ├── logging.py    # 日志配置
│   │   │   └── middleware.py # 中间件
│   │   ├── auth/             # 认证授权
│   │   │   ├── routers.py    # 认证路由
│   │   │   ├── services/     # 认证服务
│   │   │   ├── api_key.py   # API Key认证
│   │   │   └── dependencies.py # 依赖注入
│   │   ├── tenant/           # 租户管理
│   │   ├── alert/            # 告警核心
│   │   │   ├── models.py     # 数据模型
│   │   │   ├── routers.py    # API路由
│   │   │   ├── schemas.py    # Pydantic Schema
│   │   │   └── services/      # 业务逻辑
│   │   ├── rule/             # 规则引擎
│   │   └── notify/           # 通知系统
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 单元测试
│   └── main.py               # 应用入口
├── frontend/                  # React前端
│   ├── src/
│   │   ├── pages/            # 页面组件
│   │   ├── components/        # 通用组件
│   │   ├── services/          # API服务
│   │   └── stores/            # 状态管理
│   └── package.json
├── docker/                    # Docker配置
├── .github/workflows/          # CI/CD配置
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
聚合检查 → 规则匹配(AND/OR条件) → 通知队列 → 多渠道发送
```

## 核心概念
```
接入 → 指纹生成 → 去重检查 → 抑制检查 → 聚合检查 → 规则匹配 → 通知发送
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

# AI (可选)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
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
GET    /api/v1/tenants/{id}      # 获取租户详情
PUT    /api/v1/tenants/{id}      # 更新租户
GET    /api/v1/tenants/public    # 获取公开租户列表（注册时使用）
```

### Webhook（多租户）
```
POST   /api/v1/webhooks/{tenant_slug}/{source_type}  # 接收告警（多租户版本）
GET    /api/v1/tenants/{id}/webhook-key              # 获取 Webhook URL 信息
POST   /api/v1/tenants/{id}/webhook-key              # 生成/重置 Webhook API Key
```

**多租户 Webhook URL 结构:**
```
/api/v1/webhooks/{tenant_slug}/prometheus
/api/v1/webhooks/{tenant_slug}/grafana
/api/v1/webhooks/{tenant_slug}/aliyun
/api/v1/webhooks/{tenant_slug}/custom
```

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
GET    /api/v1/alerts             # 告警列表
GET    /api/v1/alerts/stats        # 告警统计
GET    /api/v1/alerts/{id}         # 告警详情
PUT    /api/v1/alerts/{id}        # 更新告警
GET    /api/v1/alerts/diagnose/{trace_id}  # 诊断
```

### 规则
```
GET    /api/v1/rules              # 规则列表
POST   /api/v1/rules              # 创建规则
GET    /api/v1/rules/{id}         # 规则详情
PUT    /api/v1/rules/{id}        # 更新规则
DELETE /api/v1/rules/{id}        # 删除规则
POST   /api/v1/rules/test        # 测试规则
```

### 通知渠道
```
GET    /api/v1/channels           # 渠道列表
POST   /api/v1/channels           # 创建渠道
PUT    /api/v1/channels/{id}      # 更新渠道
```

### 健康检查
```
GET /health          # 健康检查
GET /health/ready   # 就绪探针 (检查数据库/Redis)
GET /health/live    # 存活探针
```

## 开发指南

### 添加新的告警源适配器

1. 在 `backend/apps/alert/adapters/` 创建适配器类
2. 继承 `AlertAdapter` 基类
3. 实现 `parse()` 方法

```python
class PrometheusAdapter(AlertAdapter):
    async def parse(self, raw_data: dict) -> AlertCreate:
        # 实现解析逻辑
        return AlertCreate(...)
```

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

## 许可证

MIT License
