# Webhook 告警模拟测试

本文档提供用于本地或测试环境模拟告警的 `curl` 命令，无需在阿里云控制台真实触发即可验证 SentinelX 的接收与恢复逻辑。

## 前置条件

1. 后端服务已启动（Docker 默认映射为 `http://localhost:8001`，直连一般为 `http://localhost:8000`）。
2. 已在「告警提供商」中创建对应类型的告警源，并记下 `client_id`。
3. 若租户配置了 Webhook API Key，请求需携带 `X-API-Key` Header。

### 环境变量（可选）

```bash
export BASE_URL="http://localhost:8001"
export TENANT_SLUG="sentinelx"
export CLIENT_ID="a1b2c3d4"          # 告警源 client_id
export API_KEY="your-webhook-api-key" # 未配置 Key 时可省略对应 -H
```

### Webhook URL 格式

```
POST {BASE_URL}/api/v1/webhooks/{tenant_slug}/{source_type}/{client_id}
```

| source_type   | 说明                 | Content-Type                          |
|---------------|----------------------|---------------------------------------|
| `aliyun_cms`  | 阿里云云监控 1.0     | `application/x-www-form-urlencoded` 或 JSON |
| `aliyun_cms2` | 阿里云云监控 2.0     | `application/json`                    |

认证：Header `X-API-Key: <WEBHOOK_API_KEY>`（租户已配置时必填）。

---

## 阿里云 CMS 1.0

CMS 1.0 真实回调为 URL-encoded 表单；统一 Webhook 端点也支持 JSON。

**关键字段**：`lastTime`、`rawMetricName`、`alertState`（`ALERT` 触发，`OK` 恢复）。

**告警键**：`aliyun_cms-{alertName}-{rawMetricName}-{instance_id}`（`lastTime` 不参与，避免指纹漂移）。

**恢复关联**：恢复请求的 `alertName`、`rawMetricName`、`instanceId`（或 `dimensions` 中的 `instanceId`）须与触发时一致。

### 1.0 — 触发（form-urlencoded，推荐）

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/aliyun_cms/${CLIENT_ID}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: ${API_KEY}" \
  --data-urlencode "alertState=ALERT" \
  --data-urlencode "triggerLevel=WARN" \
  --data-urlencode "alertName=ECS-CPU高使用率" \
  --data-urlencode "rawMetricName=CPUUtilization" \
  --data-urlencode "metricName=CPUUtilization" \
  --data-urlencode "namespace=acs_ecs_dashboard" \
  --data-urlencode "expression=\$Average>75" \
  --data-urlencode "curValue=82.5" \
  --data-urlencode "lastTime=5分钟" \
  --data-urlencode "instanceName=test-ecs-01" \
  --data-urlencode "dimensions={instanceId=i-bp1ci8xv2kn34ekzctzd}"
```

### 1.0 — 恢复（`alertState=OK`）

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/aliyun_cms/${CLIENT_ID}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: ${API_KEY}" \
  --data-urlencode "alertState=OK" \
  --data-urlencode "triggerLevel=INFO" \
  --data-urlencode "alertName=ECS-CPU高使用率" \
  --data-urlencode "rawMetricName=CPUUtilization" \
  --data-urlencode "metricName=CPUUtilization" \
  --data-urlencode "namespace=acs_ecs_dashboard" \
  --data-urlencode "expression=\$Average>75" \
  --data-urlencode "curValue=60.0" \
  --data-urlencode "lastTime=0分钟" \
  --data-urlencode "instanceName=test-ecs-01" \
  --data-urlencode "dimensions={instanceId=i-bp1ci8xv2kn34ekzctzd}"
```

### 1.0 — 触发（JSON）

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/aliyun_cms/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "alertState": "ALERT",
    "triggerLevel": "CRITICAL",
    "alertName": "RDS-连接数过高",
    "rawMetricName": "ConnectionUsage",
    "metricName": "ConnectionUsage",
    "namespace": "acs_rds_dashboard",
    "expression": "$Average>80",
    "curValue": "91.2",
    "lastTime": "3分钟",
    "instanceName": "test-rds-01",
    "dimensions": "{instanceId=rm-bp1xxxxxxxxxx}"
  }'
```

### 1.0 — 专用 form 路径（已废弃）

不绑定 `client_id`，统计不会记到具体告警源；日常测试请使用 `/aliyun_cms/{client_id}`。

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/aliyun_cms/form" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: ${API_KEY}" \
  --data-urlencode "alertState=ALERT" \
  --data-urlencode "alertName=测试告警" \
  --data-urlencode "rawMetricName=CPUUtilization" \
  --data-urlencode "lastTime=1分钟"
```

### CMS 1.0 字段与严重级别

| 字段 | 说明 |
|------|------|
| `alertState` | `ALERT` 触发；`OK` 恢复；`INSUFFICIENT_DATA` 无数据（severity 降为 low） |
| `triggerLevel` | `CRITICAL` / `WARN` / `INFO` → 映射为 critical / high / info |
| `alertName` | 告警名称 |
| `rawMetricName` | 原始指标名 |
| `curValue` | 当前值 |
| `lastTime` | 持续时间（不参与 alert_key） |
| `dimensions` | 形如 `{instanceId=xxx, ...}` |

---

## 阿里云 CMS 2.0

CMS 2.0 使用 JSON 格式。

**关键字段**：`alertName`、`metricName`、`namespace`、`state`（`OK` 触发恢复逻辑）。

**告警键**：`aliyun_cms2-{alertName}-{metricName}-{namespace}`。

**恢复关联**：恢复时 `alertName`、`metricName`、`namespace` 须与触发一致。

### 2.0 — 触发

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/aliyun_cms2/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "alertName": "SLB-后端健康检查异常",
    "metricName": "UnhealthyServerCount",
    "namespace": "acs_slb_dashboard",
    "condition": "Average>=1",
    "state": "ALERT",
    "severity": "WARN",
    "dimensions": {
      "instanceId": "lb-bp1xxxxxxxxxx",
      "instanceName": "test-slb-01"
    }
  }'
```

### 2.0 — 恢复（`state=OK`）

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/aliyun_cms2/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "alertName": "SLB-后端健康检查异常",
    "metricName": "UnhealthyServerCount",
    "namespace": "acs_slb_dashboard",
    "condition": "Average>=1",
    "state": "OK",
    "severity": "INFO",
    "dimensions": {
      "instanceId": "lb-bp1xxxxxxxxxx",
      "instanceName": "test-slb-01"
    }
  }'
```

> **注意**：Webhook 恢复流程依据 `annotations.alert_state == "OK"`。`state=RESOLVED` 在适配器中仅会将 severity 降为 info，不会走与 `OK` 相同的恢复关联逻辑。

---

## 测试流程建议

1. 先执行**触发**命令，在告警列表确认状态为 `firing`。
2. 再执行**恢复**命令（字段与触发保持一致），确认同指纹告警变为 `resolved`。
3. 未配置 Webhook API Key 时，删除各命令中的 `-H "X-API-Key: ..."` 行即可。

## 相关文档

- [API 文档 — Webhook 接口](API.md#webhook-接口-webhooks)
- [README — 阿里云云监控适配器说明](../README.md#阿里云云监控10适配器)
