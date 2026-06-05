# 规则引擎测试手册

本文档提供用于本地或测试环境验证 SentinelX **规则引擎**（去重、抑制、聚合）的 `curl` 命令。风格与 [Webhook 告警模拟测试](WEBHOOK_TEST.md) 一致，可配合自定义 Webhook 注入告警，再通过 Trace 诊断确认处理结果。

## 前置条件

1. 后端服务已启动（Docker 默认映射为 `http://localhost:8001`，直连一般为 `http://localhost:8000`）。
2. PostgreSQL、Redis 已就绪；后端启动时会自动消费 `alerts_raw` 队列（无需单独启动 worker）。
3. 已有可登录账号（默认超管 `admin` / `Admin@123456`）。
4. 已在「告警提供商」中创建 **custom** 类型告警源，或按下方步骤创建。

> 告警经 Webhook 写入后会**异步**进入规则引擎，建议每次发送后等待 1～2 秒再查 Trace。

### 环境变量

```bash
export BASE_URL="http://localhost:8001"
export TENANT_SLUG="sentinelx"
export CLIENT_ID="ruletest01"   # custom 告警源 client_id，可自定义
export USERNAME="admin"
export PASSWORD="Admin@123456"
```

### 登录并获取 Token

```bash
export TOKEN=$(curl -sS -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "TOKEN=${TOKEN:0:20}..."
```

后续需 JWT 的接口均使用：

```bash
-H "Authorization: Bearer ${TOKEN}"
```

---

## 准备：创建 custom 告警源（可选）

若已有 custom 告警源，跳过本节并设置好 `CLIENT_ID`。

```bash
curl -sS -X POST "${BASE_URL}/api/v1/sources" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "规则引擎测试源",
    "code": "rule-engine-test",
    "source_type": "custom",
    "client_id": "'"${CLIENT_ID}"'",
    "description": "用于规则引擎去重/抑制/聚合测试"
  }'
```

### 发送测试告警（custom Webhook）

Webhook URL 格式：

```
POST {BASE_URL}/api/v1/webhooks/{tenant_slug}/custom/{client_id}
```

**通用触发命令**（响应含 `trace_id`，用于后续诊断）：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "rule-engine-dedup-test-001",
    "source": "rule-test",
    "title": "规则引擎测试告警",
    "content": "测试内容",
    "severity": "high",
    "labels": {
      "env": "test",
      "service": "demo",
      "cluster": "prod"
    }
  }'
```

保存返回的 `trace_id`：

```bash
export TRACE_ID=$(curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "rule-engine-dedup-test-001",
    "source": "rule-test",
    "title": "规则引擎测试告警",
    "content": "测试内容",
    "severity": "high",
    "labels": {"env": "test", "service": "demo"}
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")

echo "TRACE_ID=${TRACE_ID}"
sleep 2
```

### 查看 Trace 诊断

```bash
curl -sS "${BASE_URL}/api/v1/alerts/diagnose/${TRACE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
```

诊断响应中关注：

| 字段 | 说明 |
|------|------|
| `summary.status` | 最终状态：`duplicate` / `suppressed` / `queued` 等 |
| `summary.suppress_reason` | 抑制原因（若被抑制） |
| `flow_steps` | 去重 / 抑制 / 聚合 / 规则匹配各步骤详情 |

---

## 一、去重（Dedup）测试

去重在规则引擎流水线中**最先**执行：窗口内相同指纹/条件的重复告警会被拦截，Trace 最终状态为 `duplicate`。

### 1.1 创建指纹去重规则

按 `alert_key` 在 300 秒内去重，且仅对 `source=rule-test` 的告警生效：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/dedup-rules" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试去重-相同alert_key",
    "description": "300秒内相同 alert_key 去重",
    "priority": 100,
    "is_active": true,
    "conditions": [
      {"field": "source", "operator": "eq", "value": "rule-test"}
    ],
    "condition_mode": "and",
    "config": {
      "enabled": true,
      "dedup_type": "fingerprint",
      "fingerprint_fields": ["alert_key"],
      "window_seconds": 300
    }
  }'
```

### 1.2 触发去重

**第一次**（应通过去重，正常进入后续流程）：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "dedup-fp-001",
    "source": "rule-test",
    "title": "去重测试-第一次",
    "content": "应通过",
    "severity": "high"
  }'
```

**第二次**（相同 `alert_key`，300 秒内应被去重）：

```bash
export TRACE_DUP=$(curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "dedup-fp-001",
    "source": "rule-test",
    "title": "去重测试-第二次",
    "content": "应被去重",
    "severity": "high"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")

sleep 2
curl -sS "${BASE_URL}/api/v1/alerts/diagnose/${TRACE_DUP}" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
```

**预期**：`summary.status` 为 `duplicate`；`flow_steps` 中含 `dedup_result`，状态为 `blocked`。

### 1.3 条件模式去重

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/dedup-rules" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试去重-条件模式",
    "priority": 90,
    "conditions": [],
    "condition_mode": "and",
    "config": {
      "enabled": true,
      "dedup_type": "condition",
      "conditions": [
        {"field": "labels.dedup_tag", "operator": "eq", "value": "batch-a"}
      ],
      "condition_mode": "and",
      "window_seconds": 300
    }
  }'
```

发送两条带相同 `labels.dedup_tag` 的告警，第二条应被去重。

### 1.4 预览去重效果（不发送 Webhook）

基于历史告警预览去重分组结果：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/preview-dedup?page=1&page_size=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "deduplication_config": {
      "enabled": true,
      "dedup_type": "fingerprint",
      "fingerprint_fields": ["alert_key"],
      "window_seconds": 300
    },
    "status": "firing",
    "source": "rule-test"
  }' | python3 -m json.tool
```

### 1.5 列出 / 删除去重规则

```bash
# 列表
curl -sS "${BASE_URL}/api/v1/rules/dedup-rules" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool

# 删除（将 {rule_id} 替换为实际 ID）
curl -sS -X DELETE "${BASE_URL}/api/v1/rules/dedup-rules/{rule_id}" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 二、抑制（Suppress）测试

抑制在**去重之后**执行。匹配规则且在生效窗口内的告警会被标记为 `suppressed`，不再进入通知队列。

### 2.1 创建抑制规则（60 分钟窗口）

对 `severity=critical` 的告警抑制 60 分钟：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/suppress-rules" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试抑制-critical",
    "description": "critical 告警抑制 60 分钟",
    "priority": 100,
    "is_active": true,
    "conditions": [
      {"field": "severity", "operator": "eq", "value": "critical"}
    ],
    "condition_mode": "and",
    "config": {
      "enabled": true,
      "type": "rule_based",
      "duration_minutes": 60
    }
  }'
```

> `duration_minutes=0` 表示**永久抑制**；保存时系统会自动写入 `effective_until`。

### 2.2 触发抑制

```bash
export TRACE_SUP=$(curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "suppress-test-001",
    "source": "rule-test",
    "title": "抑制测试-critical",
    "content": "应被抑制",
    "severity": "critical",
    "labels": {"env": "test"}
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")

sleep 2
curl -sS "${BASE_URL}/api/v1/alerts/diagnose/${TRACE_SUP}" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
```

**预期**：

- `summary.status` 为 `suppressed`
- `summary.suppress_reason` 含规则名称
- `flow_steps` 中 `suppress_result` 状态为 `blocked`

### 2.3 对照组（不应被抑制）

将 `severity` 改为 `high`，应通过抑制检查：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "suppress-control-001",
    "source": "rule-test",
    "title": "抑制对照-high",
    "severity": "high"
  }'
```

### 2.4 列出抑制规则（含生效状态）

```bash
curl -sS "${BASE_URL}/api/v1/rules/suppress-rules" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
```

响应中 `suppress_in_effect: true` 表示当前仍在抑制窗口内。

### 2.5 删除抑制规则

```bash
curl -sS -X DELETE "${BASE_URL}/api/v1/rules/suppress-rules/{rule_id}" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 三、聚合（Aggregate）测试

聚合在**抑制之后**执行。相同分组键的告警在窗口内会归入同一聚合组；可通过成员接口查看组内告警。

### 3.1 创建 group_by 聚合规则

按 `alert_key` + `source` 聚合，窗口 300 秒，保存原始告警：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/aggregate-rules" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试聚合-同alert_key",
    "description": "相同 alert_key 与 source 聚合",
    "priority": 100,
    "is_active": true,
    "conditions": [
      {"field": "source", "operator": "eq", "value": "rule-test"}
    ],
    "condition_mode": "and",
    "config": {
      "enabled": true,
      "mode": "group_by",
      "group_by": ["alert_key", "source"],
      "window_seconds": 300,
      "max_count": 100,
      "store_original_alerts": true
    }
  }'
```

### 3.2 触发聚合

**第一条**（创建新聚合组）：

```bash
export ALERT1=$(curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "agg-group-001",
    "source": "rule-test",
    "title": "聚合测试-第1条",
    "severity": "high",
    "labels": {"batch": "agg-test"}
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['id'])")

echo "ALERT1=${ALERT1}"
sleep 2
```

**第二条**（相同分组键，应加入同一聚合组）：

```bash
export TRACE_AGG2=$(curl -sS -X POST "${BASE_URL}/api/v1/webhooks/${TENANT_SLUG}/custom/${CLIENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_key": "agg-group-001",
    "source": "rule-test",
    "title": "聚合测试-第2条",
    "severity": "high",
    "labels": {"batch": "agg-test"}
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")

sleep 2
curl -sS "${BASE_URL}/api/v1/alerts/diagnose/${TRACE_AGG2}" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
```

**预期**：第二条 Trace 的 `aggregate_result` 状态为 `aggregated`，`details.parent_alert_id` 指向第一条告警 ID。

### 3.3 查看聚合组成员

以第一条告警 ID 查询组内成员：

```bash
curl -sS "${BASE_URL}/api/v1/alerts/${ALERT1}/aggregated-members?page=1&page_size=20" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
```

**预期**：`alert_count >= 2`，`items` 包含组内各告警。

### 3.4 条件模式聚合

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/aggregate-rules" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试聚合-条件模式",
    "priority": 90,
    "conditions": [],
    "condition_mode": "and",
    "config": {
      "enabled": true,
      "mode": "condition",
      "conditions": [
        {"field": "labels.batch", "operator": "eq", "value": "cond-agg"}
      ],
      "condition_mode": "and",
      "window_seconds": 300,
      "max_count": 50,
      "store_original_alerts": true
    }
  }'
```

### 3.5 预览聚合效果

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/preview-aggregate?page=1&page_size=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "aggregate_config": {
      "enabled": true,
      "group_by": ["alert_key", "source"],
      "window_seconds": 300,
      "max_count": 100,
      "store_original_alerts": true
    },
    "status": "firing",
    "source": "rule-test"
  }' | python3 -m json.tool
```

### 3.6 删除聚合规则

```bash
curl -sS -X DELETE "${BASE_URL}/api/v1/rules/aggregate-rules/{rule_id}" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 四、在线测试规则条件（不发送告警）

在配置策略前，可先验证条件表达式是否匹配：

```bash
curl -sS -X POST "${BASE_URL}/api/v1/rules/test" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {"field": "severity", "operator": "in", "value": ["critical", "high"]},
      {"field": "labels.env", "operator": "eq", "value": "test"}
    ],
    "condition_mode": "and",
    "test_data": {
      "severity": "critical",
      "source": "rule-test",
      "labels": {"env": "test", "service": "demo"}
    }
  }' | python3 -m json.tool
```

**预期**：`matched: true`，`evaluated_conditions` 逐条展示各字段比较结果。

---

## 五、完整测试流程建议

按规则引擎实际执行顺序验证：

```text
1. 登录获取 TOKEN
2. 创建/确认 custom 告警源
3. 分别创建去重 / 抑制 / 聚合策略规则（建议一次只测一种，避免互相干扰）
4. 发送 Webhook 告警（保存 trace_id / alert id）
5. sleep 1～2 秒后调用 diagnose 接口确认 flow_steps
6. 测试完成后 DELETE 对应策略规则，避免影响其他测试
```

### 各场景预期 Trace 状态

| 场景 | `summary.status` | 关键 flow_step |
|------|------------------|----------------|
| 去重命中 | `duplicate` | `dedup_result` → `blocked` |
| 抑制命中 | `suppressed` | `suppress_result` → `blocked` |
| 聚合（加入已有组） | `queued` 等 | `aggregate_result` → `aggregated` |
| 聚合（新建组） | `queued` 等 | `aggregate_result` → `new_group` |
| 正常通过 | `queued` | 四步均为 `passed` / `success` |

### 常见问题

| 现象 | 可能原因 |
|------|----------|
| Trace 404 | 队列尚未消费，多等几秒；或 trace_id 写错 |
| 去重未生效 | 规则 `config.enabled` 未设为 `true`；`conditions` 未匹配；已超过 `window_seconds` |
| 抑制未生效 | 告警 `severity` 与条件不符；抑制规则已过期（`duration_minutes` 窗口结束） |
| 聚合无成员 | `store_original_alerts` 为 `false`；分组字段值不一致；窗口已过期 |

---

## 相关文档

- [Webhook 告警模拟测试](WEBHOOK_TEST.md) — 各告警源 Webhook curl 示例
- [API 文档 — 规则接口](API.md#规则接口-rules)
- [API 文档 — 诊断接口](API.md) — `GET /api/v1/alerts/diagnose/{trace_id}`
