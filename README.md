# SentinelX - 综合告警平台

企业级、多租户、高可用的综合告警平台。

## 特性

- **多租户管理**: 基于RBAC的租户隔离，支持资源配额控制
- **多源告警接入**: 支持 Prometheus、Alertmanager、阿里云、腾讯云、Zabbix 等
- **智能规则引擎**: 基于标签的路由规则，支持 AND/OR 逻辑和正则匹配
- **告警处理**: 去重、抑制、聚合、升级策略
- **多渠道通知**: 钉钉、飞书、企业微信、邮件等
- **AI增强**: LLM接入，支持根因分析和内容润色
- **诊断模式**: Trace ID 全链路追踪

## 技术栈

### 后端
- Python 3.11 + FastAPI
- PostgreSQL + TimescaleDB (时序扩展)
- Redis
- PGMQ (PostgreSQL 原生消息队列)
- SQLAlchemy + Pydantic

### 前端
- React 18 + TypeScript
- Vite
- shadcn/ui + Tailwind CSS
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

### 2. 启动服务

```bash
docker-compose -f docker/docker-compose.yml up -d
```

这将启动:
- PostgreSQL (TimescaleDB)
- Redis
- Backend API (端口 8000)
- Frontend (端口 3000)

### 3. 访问应用

- 前端: http://localhost:3000
- API 文档: http://localhost:8000/docs

### 4. 本地开发

**后端:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
SentinelX/
├── backend/                    # Python后端
│   ├── apps/
│   │   ├── core/              # 核心模块 (配置、数据库、安全)
│   │   ├── auth/              # 认证授权
│   │   ├── tenant/            # 租户管理
│   │   ├── alert/             # 告警核心
│   │   │   ├── models.py      # 数据模型
│   │   │   ├── routers.py     # API路由
│   │   │   └── services/      # 业务逻辑
│   │   ├── rule/              # 规则引擎
│   │   └── notify/             # 通知系统
│   └── main.py                # 应用入口
├── frontend/                   # React前端
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── components/         # 通用组件
│   │   ├── services/           # API服务
│   │   └── stores/             # 状态管理
│   └── package.json
├── agent/                      # 内网Agent
├── docker/                     # Docker配置
└── docs/                       # 文档
```

## 核心概念

### 告警流程
```
接入 → 指纹生成 → 去重检查 → 抑制检查 → 聚合检查 → 规则匹配 → 通知发送
```

### Trace ID 诊断
每条告警都有唯一的 12 位 Trace ID，可用于诊断告警处理全流程。

## 配置说明

### 环境变量

```env
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=sentinelx

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
JWT_SECRET_KEY=your-secret-key

# AI (可选)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
```

## API 文档

启动服务后访问 http://localhost:8000/docs 查看完整的 OpenAPI 文档。

### 认证
```
POST /api/v1/auth/login          # 用户登录
POST /api/v1/auth/refresh        # 刷新Token
GET  /api/v1/auth/me             # 当前用户信息
```

### 告警
```
POST   /api/v1/alerts             # 接收告警
GET    /api/v1/alerts             # 告警列表
GET    /api/v1/alerts/{id}        # 告警详情
GET    /api/v1/alerts/stats       # 告警统计
GET    /api/v1/alerts/diagnose/{trace_id}  # 诊断
```

### 规则
```
GET    /api/v1/rules              # 规则列表
POST   /api/v1/rules              # 创建规则
PUT    /api/v1/rules/{id}        # 更新规则
POST   /api/v1/rules/test        # 测试规则
```

## 开发指南

### 添加新的告警源适配器

1. 在 `backend/apps/alert/adapters/` 创建适配器类
2. 继承 `AlertAdapter` 基类
3. 实现 `parse()` 方法将原始数据转换为 `AlertCreate` Schema

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

## 性能优化

### 数据库层优化
- JSONB 字段使用 GIN 索引
- 使用 CTE 和窗口函数进行聚合
- TimescaleDB 自动分区

### 缓存策略
- Redis 用于去重 (5分钟窗口)
- 热点数据缓存

## 许可证

MIT License
