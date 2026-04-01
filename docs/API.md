# SentinelX API 文档

## 基础信息

- **Base URL**: `http://localhost:8001/api/v1`
- **认证方式**:
  - 用户认证: `Authorization: Bearer <JWT_TOKEN>`
  - API Key: `X-API-Key: <API_KEY>`

## 认证接口 `/auth`

### 登录

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin@123456"
}
```

**响应**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 注册

```
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "Password@123",
  "tenant_slug": "sentinelx"
}
```

> 注册后账号需管理员审批才可登录

### 刷新 Token

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

### 切换租户

```
POST /api/v1/auth/switch-tenant
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "tenant_id": 2
}
```

### 获取当前用户

```
GET /api/v1/auth/me
Authorization: Bearer <TOKEN>
```

### 获取我的权限

```
GET /api/v1/auth/permissions
Authorization: Bearer <TOKEN>
```

## 租户管理 `/tenants`

### 获取租户列表

```
GET /api/v1/tenants
Authorization: Bearer <TOKEN>
```

### 创建租户

```
POST /api/v1/tenants
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "name": "开发团队",
  "slug": "dev-team"
}
```

### 获取租户详情

```
GET /api/v1/tenants/{id}
Authorization: Bearer <TOKEN>
```

### 获取公开租户列表（注册用）

```
GET /api/v1/tenants/public
```

## Webhook 接口 `/webhooks`

### 接收告警（多租户）

```
POST /api/v1/webhooks/{tenant_slug}/{source_type}
X-API-Key: <WEBHOOK_API_KEY>
Content-Type: application/json
```

**支持的 source_type**: `prometheus`, `alertmanager`, `aliyun`, `tencent`, `huawei`, `zabbix`, `grafana`, `custom`

**Prometheus Alertmanager 格式**:
```json
{
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighCPU",
        "severity": "critical",
        "instance": "server-01"
      },
      "annotations": {
        "description": "CPU usage > 90%"
      },
      "startsAt": "2024-01-01T10:00:00Z"
    }
  ]
}
```

**自定义 Webhook 格式**:
```json
{
  "title": "告警标题",
  "content": "告警详情",
  "severity": "critical",
  "labels": {
    "cluster": "prod",
    "service": "payment"
  }
}
```

## 告警接口 `/alerts`

### 告警列表

```
GET /api/v1/alerts
Authorization: Bearer <TOKEN>
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 状态: firing/resolved/acknowledged/silenced |
| severity | string | 级别: critical/high/medium/low/info |
| source | string | 来源类型 |
| start_time | string | 开始时间 ISO 格式 |
| end_time | string | 结束时间 ISO 格式 |
| page | int | 页码 |
| page_size | int | 每页数量 |

### 告警统计

```
GET /api/v1/alerts/stats
Authorization: Bearer <TOKEN>
```

### 告警详情

```
GET /api/v1/alerts/{id}
Authorization: Bearer <TOKEN>
```

### 告警诊断

```
GET /api/v1/alerts/diagnose/{trace_id}
Authorization: Bearer <TOKEN>
```

返回告警从接收到通知的完整处理流程。

## 规则接口 `/rules`

### 规则列表

```
GET /api/v1/rules
Authorization: Bearer <TOKEN>
```

### 创建规则

```
POST /api/v1/rules
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "name": "严重告警通知",
  "conditions": [
    {"field": "severity", "operator": "in", "value": ["critical", "high"]},
    {"field": "labels.cluster", "operator": "eq", "value": "prod"}
  ],
  "condition_mode": "and",
  "actions": {
    "notify_channels": ["dingtalk-channel-1"]
  },
  "is_active": true
}
```

### 测试规则

```
POST /api/v1/rules/test
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "conditions": [
    {"field": "severity", "operator": "eq", "value": "critical"}
  ],
  "condition_mode": "and",
  "test_alert": {
    "title": "Test Alert",
    "severity": "critical",
    "labels": {}
  }
}
```

## 通知渠道 `/channels`

### 渠道列表

```
GET /api/v1/channels
Authorization: Bearer <TOKEN>
```

### 创建渠道

```
POST /api/v1/channels
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "name": "钉钉告警群",
  "channel_type": "dingtalk",
  "config": {
    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx"
  }
}
```

## 模板接口 `/templates`

### 模板列表

```
GET /api/v1/templates
Authorization: Bearer <TOKEN>
```

### 创建模板

```
POST /api/v1/templates
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "name": "默认模板",
  "channel_type": "dingtalk",
  "content": "[{{severity}}] {{title}}\n来源: {{source}}\n时间: {{fired_at}}"
}
```

## AI 接口 `/ai`

### 根因分析

```
POST /api/v1/ai/root-cause
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "alert_id": 123
}
```

### 内容润色

```
POST /api/v1/ai/polish
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "content": "原始告警内容",
  "channel_type": "dingtalk"
}
```

## 健康检查

```
GET /health          # 健康检查
GET /health/ready   # 就绪探针（检查数据库/Redis）
GET /health/live    # 存活探针
```

## 错误响应格式

```json
{
  "message": "错误描述",
  "code": "ERROR_CODE",
  "details": {}
}
```

| HTTP 状态码 | 说明 |
|------------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突（重复创建等） |
| 422 | 数据验证失败 |
| 429 | 请求过于频繁（限流） |
| 500 | 服务器内部错误 |
