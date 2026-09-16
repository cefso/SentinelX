---
feature: alerts-by-instance
status: delivered
updated: 2026-09-16
branch: feat/alerts-by-instance
commits: 9d5c44b..0de0988 # 含 rebase 后 tenant_id int 对齐提交
---

# 实例告警类型页

## Report

**What was built** — 新增实例维度告警视图：后端提供 `GET /alerts/by-instance`（实例×类型聚合）与 `GET /alerts/by-instance/alerts`（实例/类型明细），采用多字段实例识别与词边界安全的类型关键词映射；前端新增「实例告警」列表页（卡片+类型徽章）与独立明细页，侧边栏可进入，点击类型/卡片跳转明细并可进告警详情。

**Verification** — `PYTHONPATH=. pytest tests/test_by_instance.py` → 14 passed；相关告警测试子集 82 passed；`npm run type-check` → PASS；`npm run build` → PASS；`npm run lint` → 0 errors（既有 warning）。

**Journey log**
1. lcmdb 等源未写 `instance_name`，实例识别改为多字段兜底 + title 明确格式提取，避免整条标题当实例导致一告警一实例。
2. 子串关键词会误伤（amount→mount、program→ram、method 中的 eth），改为词边界/前后缀形态；Python `\\b` 不把 `_` 当边界，需补 `memory_`/`process_` 等。
3. 严重级别排序曾因 rank 符号与恒升序 `sorted()` 反转，已按 critical=0 + desc 在前修正并补测。
4. 卡片内嵌套 `<Link>` 改为 div+navigate / button，避免非法嵌套锚点。
5. 两轮独立审查后修复 major；扫描窗口 90 天 + MAX_SCAN=20000 截断由响应字段与前端提示覆盖。

## [S1] Problem

运维需要按主机/实例查看当前有哪些类型的告警（CPU、内存、磁盘等），例如「文档生产服务器」同时有 CPU、内存、磁盘告警。现有告警列表按时间/指纹组织，缺少以实例为第一视角的聚合视图，无法快速定位“哪台机器有什么问题类型”。

## [S2] Design

### 实例识别（多字段兜底）

按告警字段解析 `instance_key`，优先级：

1. `instance_name`（非空）
2. `instance_id`（非空）
3. `labels.host`
4. `labels.instance`
5. `title` 提取：仅匹配明确格式——lcmdb「… 的 [类型:对象]」取「的」前名称；或 `host/主机/实例: xxx`。**不**把整条标题截断当实例，避免一告警一实例
6. `labels.ip`
7. 以上皆无 → `__unknown__`（展示为「未识别实例」）

lcmdb 无 `instance_name` 时，优先用标题首段（如「文档生产服务器 的 [磁盘:Disk]」→「文档生产服务器」）作为聚合键，IP 仅作辅助展示。

**入库固化（2026-09-16）**：lcmdb 适配器在解析时把标题首段写入 `alerts.instance_name`，新告警无需运行时再解析标题；历史数据可用 `python -m scripts.backfill_lcmdb_instance_name [--apply]` 回填。未回填的旧数据仍走查询时兜底逻辑。

同时返回展示元数据：`instance_name`、`instance_id`、`ip`（`labels.ip`）、`source`。

同一实例的多条告警若解析出相同 `instance_key` 则归为一组；`ip` 与名称冲突时以更高优先级字段为准，IP 仅作辅助展示。

### 告警类型分类（关键词映射）

对 `metric_name`、`alert_key`、`title`、`labels` 相关值拼接后做大小写不敏感正则匹配，映射到固定类型码。短/易误伤 token 使用词边界或前后缀形态，避免 `amount→mount`、`program→ram`、`method→net` 等误伤：

| type_code | type_label | 匹配模式 |
|-----------|------------|----------|
| cpu | CPU | cpu, processor, 处理器 |
| memory | 内存 | `\bmem(?:ory)?\b`, memory_, _memory, meminfo, mem_, 内存, `\bram\b` |
| disk | 磁盘 | disk, partition, `\bmount\b`, mount_, mountpoint, 磁盘, 存储, filesystem |
| process | 进程 | `\bprocess(?:es)?\b`, process_, _process, 进程, `.jar`, `\bjar\b`, `\bjava\b`, java_ |
| network | 网络 | network, bandwidth, `\bnet\b`, net_, net., netdev, 网卡, 网络, 流量, `\beth\d*\b` |
| other | 其他 | 兜底 |

匹配顺序：cpu → memory → disk → process → network → other。首个命中即返回。

### 后端 API

权限：与列表一致，依赖 `get_current_tenant_id`（无需额外权限码）。

#### `GET /api/v1/alerts/by-instance`

Query：

- `status`: 可选，`firing`/`resolved`/`suppressed`；省略=全部（默认）
- `severity`: 可选
- `source`: 可选
- `keyword`: 可选，对 `instance_key` / `instance_name` / `ip` 子串过滤（大小写不敏感）
- `page` / `page_size`: 实例分页，默认 1/20，page_size ≤ 100
- `sort_by`: `alert_count`（默认）| `max_severity` | `last_fired_at`
- `sort_order`: `desc`（默认）| `asc`

聚合实现：

1. 按 tenant + status/severity/source 过滤，排除 `status=aggregated` 子告警（与列表 hide_aggregated_children 一致）
2. 限制扫描窗口：`fired_at >= now - 90d`，且最多扫描最近 `MAX_SCAN=20000` 条（按 fired_at desc）
3. 在 Python 中按实例识别与类型分类分组
4. 实例级分页排序

Response：

```json
{
  "items": [
    {
      "instance_key": "文档生产服务器",
      "instance_name": "文档生产服务器",
      "instance_id": null,
      "ip": "10.0.0.8",
      "sources": ["lcmdb"],
      "alert_count": 5,
      "firing_count": 3,
      "max_severity": "critical",
      "last_fired_at": "2026-09-16T08:00:00Z",
      "types": [
        {"type": "cpu", "type_label": "CPU", "count": 2, "firing_count": 1, "max_severity": "critical"},
        {"type": "disk", "type_label": "磁盘", "count": 1, "firing_count": 1, "max_severity": "high"}
      ]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "scanned": 1200,
  "scan_truncated": false
}
```

#### `GET /api/v1/alerts/by-instance/alerts`

展开某实例某类型下的告警明细。

Query：

- `instance_key`（必填，URL 编码）
- `type`（必填，type_code）
- `status` / `severity` / `source` 同上
- `page` / `page_size`

实现：在扫描窗口内匹配 instance_key + type，返回分页 `AlertResponse` 列表（复用 `build_alert_response`）。

Response：

```json
{
  "items": [ /* AlertResponse[] */ ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

### 前端页面（独立页面，非内联展开）

**列表页 ` /alerts/by-instance`**

- 导航：侧边栏「告警」子项「实例告警」
- 布局：实例卡片网格（响应式，1–3 列）
  - 卡片头：实例名、IP、最高严重级别徽章、告警总数、最近触发时间
  - 类型徽章区：CPU(2) / 内存(1) / 磁盘(1) 等，带类型色点
  - **点击类型徽章 → 跳转独立明细页**（不卡片内展开）
- 顶部筛选：状态 Tab（全部/未恢复/已恢复）、实例关键词搜索、手动刷新
- 卡片整体可点击进入该实例全部类型明细（type 省略=全部）

**明细页 `/alerts/by-instance/detail?instance_key=...&type=...&status=...`**

- 必须注册在 `/alerts/:id` 之前
- 页头：实例展示名（`name` query）、IP、类型筛选 Chip（全部 + 各类型）、状态 Tab、返回列表
- 主体：告警明细表（标题、级别、状态、指标、触发时间、来源）
- 行点击跳转 `/alerts/:id`
- 分页复用现有 `Pagination` 组件
- 使用 React Query：列表页调 by-instance，明细页调 by-instance/alerts
- 空态、加载态与现有未恢复告警页风格一致（shadcn/Tailwind + lucide 图标）

### 错误行为

- 扫描截断时响应带 `scan_truncated: true`，前端展示轻提示「仅统计最近扫描窗口内告警」
- `instance_key` 未匹配任何告警 → `items: []`
- 未认证 → 401（现有鉴权链）

### 测试边界

- 实例识别：instance_name 优先；无名称时 ip；title 提取 lcmdb 格式；全空 → `__unknown__`
- 类型分类：CPU/内存/磁盘/进程/网络/其他；多关键词命中取优先级；大小写
- 分组：同 instance_key 聚合 count/severity
- API 单测：过滤、分页、instance+type 明细查询（可用内存侧逻辑函数测，不依赖真实 DB 的纯函数优先）

## [S3] Out of Scope

- 不修改各告警适配器写入逻辑（不强制补 instance_name）
- 不新增数据库列/迁移
- 不做实例拓扑、历史趋势图、批量静默
- 不实现跨租户实例视图

## Tasks

- [x] T1: 后端实例识别与类型分类纯函数 + 单元测试 — acceptance: 纯函数覆盖优先级/关键词/未知实例，pytest 通过 (covers: S2)
- [x] T2: `GET /alerts/by-instance` 与 `GET /alerts/by-instance/alerts` API + schema — acceptance: 路由可注册，返回结构符合设计，集成到 alert routers (covers: S2; depends: T1)
- [x] T3: 前端类型/服务与 `/alerts/by-instance` 列表页 + `/alerts/by-instance/detail` 明细页 + 导航/路由 — acceptance: 卡片展示实例与类型徽章，点击类型进入独立明细页，可跳告警详情 (covers: S2; depends: T2)
- [x] T4: 全量验证 pytest + tsc --noEmit — acceptance: 既有相关测试与 type-check 通过 (covers: S2; depends: T1, T2, T3)
