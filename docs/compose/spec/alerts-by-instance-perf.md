---
feature: alerts-by-instance-perf
status: in-progress
updated: 2026-09-17
branch: perf/alerts-by-instance
commits: b09bada.. # 填充于交付
---

# 实例告警性能优化

## Report

## [S1] Problem

「实例告警」列表接口 `GET /alerts/by-instance` 与明细接口 `GET /alerts/by-instance/alerts` 每次请求都会：

1. 按 90 天窗口 + `MAX_SCAN=20000` 拉取**完整 Alert ORM 对象**（含 labels/raw_data/content 等大 JSON）；
2. 在 Python 中对每条告警做正则类型分类（`TYPE_RULES` 多模式 `re.search`）与多字段实例识别；
3. 列表再内存分组/排序/分页，明细再线性过滤后分页。

告警量增大时接口 CPU 与内存开销随扫描条数线性上升，响应明显变慢；明细页为查一页数据仍支付全量扫描成本。

## [S2] Design

### 方案对比：新列 vs 写入 labels

| 维度 | **A. 新增独立列** `instance_key` / `alert_type` | **B. 写入现有 `labels` JSON** |
|------|-----------------------------------------------|------------------------------|
| 查询形态 | `WHERE instance_key=?` / `GROUP BY instance_key`，标准 B-tree | `WHERE labels->>'instance_key'=?` / `GROUP BY labels->>'instance_key'` |
| 索引 | 普通复合索引即可，明细 `(tenant_id, instance_key, alert_type, fired_at)` 高效 | 需 **表达式索引** `ON (tenant_id, (labels->>'instance_key'))` 等；**为性能仍要做迁移**，并未省掉 schema 变更 |
| 性能 | 列等值/分组走索引，成本稳定 | 无表达式索引时接近全表+JSON 提取；有索引也可用，但计划与统计信息更脆 |
| 语义污染 | 派生字段独立，职责清晰 | `labels` 表示来源标签；塞入派生键会干扰规则引擎匹配、通知模板变量、前端标签展示、导出 |
| 类型与约束 | `String(32)` 枚举语义，可加 Check | JSON 字符串，约束弱，易被 webhook/adapter 误覆盖 |
| 写入 | 两列赋值 | `labels = {**labels, "instance_key": ...}`，与来源标签合并，回滚/审计困难 |
| 回填 | `UPDATE alerts SET instance_key=...` | `jsonb_set`，批量与幂等更麻烦 |
| 与「实例告警」页契合 | 聚合键/类型码与 API 字段一一对应 | 每次查询都要 JSON 提取再映射 |

**结论（推荐 A）**：目标是 SQL 聚合与明细索引分页；B 若也要达到同等性能，仍需表达式索引迁移，却额外污染 `labels` 业务语义。独立列更贴合本功能，且不改变对外 API。

> 若你更倾向 B，实现上仍建议：只把派生值写入 labels 的私有前缀键（如 `__instance_key` / `__alert_type`），并建表达式索引；规则/展示层需显式忽略下划线前缀键。当前默认按 **A** 实现。

### 总体策略（方案 A）

反规范化 `instance_key` / `alert_type` 到 `alerts` 表，写入时固化；列表改 **SQL GROUP BY 聚合**，明细改 **SQL WHERE + LIMIT/OFFSET**。历史数据用回填脚本补齐。API 请求参数与响应结构保持兼容。

### 数据库变更

`alerts` 新增两列（均可空，历史行先 NULL 再回填）：

| 列 | 类型 | 说明 |
|----|------|------|
| `instance_key` | `String(256)` | 实例聚合键；无法识别时写 `__unknown__` |
| `alert_type` | `String(32)` | `cpu` / `memory` / `disk` / `process` / `network` / `other` |

索引：

- `idx_alerts_tenant_instance_key (tenant_id, instance_key)`
- `idx_alerts_by_instance_detail (tenant_id, instance_key, alert_type, fired_at DESC)`

Alembic revision：`add_alert_instance_key_type`（down_revision 指向 `20260916_unify_tenant_id` 对应 head）。

### 写入路径固化（详细设计）

#### 1. 单一计算入口

新增纯函数（`apps/alert/services/by_instance.py`）：

```python
def apply_instance_denorm(alert: Alert) -> None:
    """就地写入 alert.instance_key / alert.alert_type。仅依赖 title/labels/
    metric_name/alert_key/instance_name/instance_id，与查询期逻辑同源。"""
    info = extract_instance(alert)
    alert.instance_key = info["instance_key"] or UNKNOWN_INSTANCE_KEY
    alert_type, _ = classify_alert_type(alert)
    alert.alert_type = alert_type or "other"
```

约束：

- **规则零分叉**：只调用现有 `extract_instance` / `classify_alert_type`，禁止在写入路径另写一套正则或优先级。
- **永不为 NULL 的业务语义**：无法识别实例 → `instance_key='__unknown__'`；无法归类 → `alert_type='other'`。列允许 NULL 仅用于「历史未回填」过渡态。
- **幂等**：对同一字段集重复调用结果相同；不依赖 `id`/`created_at`/DB 状态。

#### 2. 调用点（构建 Alert 之后、`db.add` 之前）

当前生产写入只有两处 `Alert(...)` 构造（均在 `apps/alert/routers.py`）：

| 构造点 | 用途 | 处理 |
|--------|------|------|
| `_build_alert` (≈L156) | Webhook / 批量 / OK 恢复创建 | 构造完成后立即 `apply_instance_denorm(alert)` |
| `create_alert` POST `/alerts` (≈L468) | 直接创建接口 | **改为复用 `_build_alert`**，去掉重复构造，从根上消除漏写风险 |

`create_alert` 与 `_build_alert` 差异仅 status（固定 `firing`）与 `resolved_at`，统一到：

```python
alert = _build_alert(request, tenant_id, request.source_id, "firing", trace_id)
```

指纹逻辑保持原 `create_alert` 行为（`request.fingerprint or generate_fingerprint(...)`），与 `_build_alert` 内逻辑一致。

**不改各 adapter**（lcmdb/aliyun 等）：它们只产出 `AlertCreate` 字段，固化发生在统一构建层。

**不做** SQLAlchemy `before_insert` 事件：规则是业务语义而非 ORM 钩子，显式调用便于测试与审计。

#### 3. 字段语义与优先级（与查询期一致）

`instance_key` 计算优先级（`extract_instance`）：

1. `instance_name` 非空 → key=instance_name  
2. 否则 `instance_id`  
3. 否则 `labels.host`  
4. 否则 `labels.instance`  
5. 否则 title 提取（lcmdb「xx 的 [..]」或 `host/主机/实例: xxx`）  
6. 否则 `labels.ip`  
7. 否则 `__unknown__`

`alert_type`：对 `metric_name` + `alert_key` + `title` + labels 中 `alertname`/`metric_name`/`trigger_name` 拼接后，按 cpu → memory → disk → process → network → other 首个命中。

`instance_key` 仅作聚合键；展示用 `instance_name`/`instance_id`/`ip` **不**再写入新列，列表 SQL 从行内既有列聚合（见列表节）。

#### 4. 与 schema/API 的关系

- `AlertCreate` / `AlertResponse` **不**新增这两个字段的对外写入要求；客户端仍只传原始字段。
- 内部列不进入 webhook 响应的必填契约；若 `AlertResponse` 为 `from_attributes` 自动带出，允许可选暴露但不作为前端依赖。
- 规则引擎、通知模板等读取路径继续用 title/labels/metric 等原始字段，**不**依赖反规范化列（避免写入延迟或回填不全影响路由）。

#### 5. 回填与写入的同一性

回填脚本对每行构造的最小对象（或直接用 ORM 行）调用同一 `apply_instance_denorm`，保证：

```
写入路径(instance_key, alert_type) ≡ 回填路径(instance_key, alert_type)
```

单测断言：同一字段集分别走「构建时固化」与「回填函数」得到相同两列。

### 历史回填

新增 `backend/scripts/backfill_alert_instance_fields.py`：

- 默认 dry-run，`--apply` 写入；
- 批处理：`WHERE instance_key IS NULL OR alert_type IS NULL`，按 `id` 升序分批（默认 500）；
- 每条用与写入相同的纯函数计算后 `UPDATE`；
- 识别失败写 `instance_key='__unknown__'`，分类失败写 `alert_type='other'`。

### `GET /alerts/by-instance`（列表）

去掉「拉 2 万条到 Python」路径。保留 query 参数：`status` / `severity` / `source` / `keyword` / `page` / `page_size` / `sort_by` / `sort_order`。

过滤条件（SQL WHERE）：

- `tenant_id = :t`
- `status != 'aggregated'`
- 可选 `status` / `severity` / `source`（与现网一致）
- 可选扫描窗口：`fired_at >= now - window_days`，默认 **90 天**（query 参数 `window_days` 可选，范围 1–365，缺省 90）
- `instance_key IS NOT NULL`（回填后基本全覆盖；查询时 `COALESCE(instance_key,'__unknown__')` 兜底聚合）

聚合 SQL 形态（PostgreSQL）：

```sql
SELECT
  COALESCE(instance_key, '__unknown__') AS instance_key,
  COUNT(*) AS alert_count,
  COUNT(*) FILTER (WHERE status = 'firing') AS firing_count,
  MAX(fired_at) AS last_fired_at,
  MAX(instance_name) FILTER (WHERE instance_name IS NOT NULL AND instance_name <> '') AS instance_name,
  MAX(instance_id) FILTER (WHERE instance_id IS NOT NULL AND instance_id <> '') AS instance_id,
  MAX(labels->>'ip') FILTER (WHERE labels ? 'ip') AS ip,
  MIN(CASE severity
        WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2
        WHEN 'low' THEN 3 WHEN 'info' THEN 4 ELSE 5 END) AS severity_rank,
  array_remove(array_agg(DISTINCT source), NULL) AS sources
FROM alerts
WHERE ...
GROUP BY 1
```

- **keyword**：在 **HAVING** 上对聚合后的 `instance_key` / `MAX(instance_name)` / `MAX(ip)` 做 ILIKE 子串（大小写不敏感），对齐旧「先分组再过滤卡片」语义，避免组内部分行命中导致计数被切开。
- **排序**：`alert_count` / `max_severity`（用 severity_rank）/ `last_fired_at`，asc/desc；同一排序键平局时用 `instance_key` 稳定排序。
- **分页**：`COUNT(*) OVER()` 得 total，`LIMIT/OFFSET` 取当页。
- **类型徽章**：对当页 `instance_key IN (...)` 再跑一次轻量聚合：

```sql
SELECT instance_key, alert_type, COUNT(*) AS count,
       COUNT(*) FILTER (WHERE status='firing') AS firing_count,
       MIN(severity_rank) ...
FROM alerts
WHERE tenant_id=? AND COALESCE(instance_key,'__unknown__') IN (...)
  AND <同列表过滤>
GROUP BY 1, 2
```

- **sources 展示**：列表优先用 `alert_sources.name`，通过 `LEFT JOIN alert_sources` 聚合 `DISTINCT COALESCE(src.name, alerts.source)`；join 成本可接受（源数量少）。若实现时选择分步查源名 map 再在 Python 拼装，也允许，但**禁止**再全量拉 Alert。
- **response**：结构不变。`scanned` = 过滤窗口内匹配告警总数（与 total 聚合前条数一致的计数，或单独 `COUNT`）；`scan_truncated` 恒为 `false`（不再截断扫描）。

### `GET /alerts/by-instance/alerts`（明细）

不再全表扫描：

- WHERE：`tenant_id` + 现有过滤 + **索引友好** instance_key 谓词：`__unknown__` → `(instance_key IS NULL OR instance_key = '__unknown__')`（兼容未回填 NULL 与写入哨兵），否则 `instance_key = :k`（避免 `COALESCE(col)=?` 导致 B-tree 失效）
- 可选 `alert_type = :type`（`COALESCE(alert_type,'other') = :type`）
- `ORDER BY fired_at DESC, id DESC`
- `LIMIT/OFFSET` 分页；`COUNT(*)` 得 total
- 仅 `SELECT` 明细所需字段（或复用现有 Alert 列表 select 模式），`build_alert_response` 组装
- `source_name` 通过 `LEFT JOIN alert_sources` 一并取回

### 错误与边界

- 未认证 → 401（不变）
- `instance_key` 无匹配 → `items: []`（不变）
- 窗口外或未回填的 NULL key 行：回填后不再依赖查询时标题解析；**部署必须执行** `python -m scripts.backfill_alert_instance_fields --apply`，否则历史行会聚合成单张「未识别实例」大卡
- `window_days` 非法 → 422

### 测试边界

- 写入：`_build_alert` 后 `instance_key`/`alert_type` 与纯函数结果一致（含 `__unknown__` / `other`）
- 纯函数既有 15 项 `test_by_instance.py` 保持通过
- 回填：dry-run 不写库；对构造数据 apply 后列值正确
- 列表/明细查询逻辑：优先抽可单测的 severity_rank 映射与排序键函数；有 DB fixture 时再测聚合 SQL，无 DB 时不要求
- 前端 `npm run type-check` 仍通过（类型中 `scanned`/`scan_truncated` 字段保留）

## [S3] Out of Scope

- Redis/内存缓存
- 修改类型关键词规则或实例识别优先级
- 前端页面重构（仅保证类型与展示兼容）
- 拓扑、趋势图、批量静默
- 自动在迁移里做 2 万+ 行 Python 回填（迁移只加列/索引，回填独立脚本）

## Tasks

- [x] T1: Alembic 迁移：`alerts.instance_key` / `alert_type` + 索引 — acceptance: upgrade/downgrade 可执行，模型字段存在 (covers: S2)
- [x] T2: 写入路径 `_build_alert` 固化 instance_key/alert_type + 单测 — acceptance: 创建告警后两列与 extract/classify 一致 (covers: S2; depends: T1)
- [x] T3: 列表接口改 SQL 聚合（GROUP BY + 类型子查询 + 分页排序 keyword）— acceptance: 不再调用 fetch_alerts_for_scan；响应结构兼容；相关单测/逻辑测试通过 (covers: S2; depends: T1)
- [x] T4: 明细接口改 SQL WHERE+分页 — acceptance: 按 instance_key/type/分页查询，不再全量扫描 (covers: S2; depends: T1)
- [x] T5: 回填脚本 `backfill_alert_instance_fields.py`（dry-run/--apply，分批）— acceptance: 脚本可执行，逻辑覆盖 NULL 列 (covers: S2; depends: T2)
- [x] T6: 全量验证 pytest 相关用例 + 前端 type-check — acceptance: 既有与新增测试通过，type-check PASS (covers: S2; depends: T2, T3, T4, T5)
