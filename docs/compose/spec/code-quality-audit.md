---
feature: code-quality-audit
status: delivered
updated: 2026-09-17
branch: audit/code-quality
commits: 000eb7aa618ebd661cddc696f185e7a2a8f4ea52..<pending>
---

# SentinelX 全面代码审计（类型一致性 / Bug / 优化）

## Report

**What was built**

对 SentinelX 前后端做了均衡全面审计（类型契约、安全/正确性、性能/可维护性），并在本分支实施了 Critical/High 与低风险 Medium 修复。修复覆盖：多租户越权（详情密钥、webhook key、跨租户角色/密码/用户列表/权限重置、升级任务）、Webhook API Key 校验失效与 str/int 比较、API Key 权限门控与创建 Body 契约、处置记录读写 action 对齐、通知 channel 租户边界、基础 SSRF 拦截、注册页租户列表契约、告警筛选 `assignee_id`、前端类型对齐与 keyword 防抖/导出 N+1 限制。

**Verification**

- `backend`: `pytest tests/ -q` → **PASS 177**（含新增 `test_tenant_auth_security.py`、`test_alert_security.py` 共 53 项）
- `frontend`: `tsc --noEmit` → **PASS**
- 静态 import 检查通过
- 独立 Review：**approve**，无阻塞 Critical；非阻塞项已记入下方

**Journey log**

1. 并行三路审计（契约/安全/性能）后发现安全面问题密度最高，优先落地租户路由与 webhook 认证。
2. `verify_api_key` 原先对 bcrypt hash 做明文 compare_digest，正确 key 必失败且不传 key 放行——修复为 `pwd_context.verify` + 配置了 key 则强制校验。
3. 处置记录历史上 write/read action 命名不一致导致列表恒空；统一为 `dispose_*` 存储并在读取时映射回前端枚举。
4. 子代理无法跑 bash，由主会话完成 pytest/tsc 验证并修正 2 个测试自身断言问题。
5. 未在本轮实施的大项（见「未修复/建议」）包括 JWT 权限快照、OpenAPI codegen、复合索引迁移、路由级代码分割、指纹 flapping SQL 下推。

### 已修复（Critical / High / 部分 Medium）

#### 类型与 API 契约

| 级别 | 问题 | 修复 |
|------|------|------|
| Critical | `POST /auth/api-keys` 后端按 query 解析，前端发 JSON body → 422 | 增加 `APIKeyCreateRequest` Body 模型 |
| Critical | 处置记录写入 `acknowledged/...`，读取 `dispose_%` → 恒空 | 写入 `dispose_*`，读取 strip 前缀映射回 `note/acknowledge/resolve/silence` |
| High | `GET /tenants/public` 裸数组 vs 前端 `{tenants}` → 注册选租户恒空 | 前端按数组解析 |
| High | Webhook 日志批量 `ids` 后端未实现 | 支持 `ids: list[int]`，`dismiss_all` 改单条 UPDATE |
| Medium | `/alerts` 未接收 `assignee_id` | Query + 过滤已加 |
| Medium | `AlertSource.is_active` 前端误标 boolean | 共享 `active\|inactive` 类型 |
| Medium | `AlertFilter.severity` 类型数组 vs API 单值 | 前端改为 `string` |
| Medium | Webhook 日志 `start_time/end_time` 后端不支持 | 已实现 |
| Low | 登录 Zod min 与后端不一致 | username min3 / password min6 |

#### 安全与正确性

| 级别 | 问题 | 修复 |
|------|------|------|
| Critical | `GET /tenants/{id}` 任意用户可读 `api_token`/`webhook_api_key` | 成员校验；响应去掉密钥 |
| Critical | webhook-key 端点无租户边界/权限 | `tenants:read/write` + 同租户或 `is_system` |
| Critical | `PUT /users/{id}/role` 可跨租户提权 | 非 system 限制 `tr.tenant_id == current` |
| Critical | 改密码可免旧密码改他人 | 自改必验 `old_password`；改他人需 `users:write` |
| Critical | `GET /users` 全库枚举 | 仅当前租户成员 + `users:read` |
| Critical | reset-permissions 清掉用户所有租户关联 | 非 system 仅当前租户 |
| Critical | API Key 创建/列表/撤销无权限 | `api_keys:read/write/delete` |
| Critical | Webhook API Key：正确 key 必失败 / 不传放行 | bcrypt verify；配置了 key 则强制 |
| Critical | `str(tenant_id) != tenant_id` 永久 404 | 统一 int 比较（含 Redis 诊断分支） |
| Critical | 升级检查全库扫描 | `check_escalations(tenant_id)` + candidates SQL 过滤 |
| High | Refresh 不校验 `is_approved` | 登录侧校验对齐 |
| High | 通知发送不校验 channel 租户 | sender + worker 双重校验 |
| High | Webhook 渠道 SSRF | 拒绝 localhost/私网/链路本地等 |
| High | `PUT /alerts/{id}` 可任意改写状态 | 字段白名单 + 非法迁移 400 |
| High | 处置 `old_value` 在状态更新后写入 | 先快照 `previous_status` |
| High | `list_tenants` 可列全部租户 | 非 system 仅所属租户 |
| Medium | `toggle_source` 无写权限；source code 查重缺 tenant | 已修 |

#### 性能（本轮实施）

| 级别 | 问题 | 修复 |
|------|------|------|
| High | 告警列表 keyword 每键 refetch | 400ms debounce + Enter/搜索立即提交 |
| High | 导出对每条告警请求 dispose（N+1） | 仅当前页拉取 dispose；全量/区间导出置空 |
| Medium | 渠道 Secret 明文输入框 | 改为 password 输入 |

### 未修复 / 后续建议（按优先级）

1. **High** JWT 权限/超级用户为陈旧快照，降权最长 7 天不生效 — 建议关键写路径查 DB 或权限版本号。
2. **High** 指纹视图 flapping 无界拉取全量历史 + 分页后过滤导致 total 失真 — 下推 SQL 窗口聚合。
3. **High** 批量接警循环内 flush/查指纹/发 MQ — 批量化。
4. **Medium** 缺 `(tenant_id, status, fired_at)` 复合索引；`idx_alerts_labels` B-tree 低价值 — Alembic 迁移。
5. **Medium** 通知渠道 config 响应仍含完整密钥（后端） — 响应脱敏。
6. **Medium** 前端无路由级 code splitting（recharts/react-markdown 进主包）。
7. **Medium** `/alerts/stats` 全表 distinct、列表页 6–7 并发接口 — overview 合并 + 缓存。
8. **Medium** 规则 `regex` ReDoS；API Key 虚拟用户 id=0 全权；云指标全局表无租户边界。
9. **Low/Info** 响应补 `response_model`、分页契约统一、OpenAPI codegen 共享类型、`get_db` 无条件 commit、前端 token localStorage、register 用户名/邮箱存在性枚举。

### Review 备注（非阻塞）

- dispose silence 目前只写 history，未写 `silenced_until`
- SSRF 为基础拦截（创建时），不做 DNS 解析；存量 channel 发送前不重校验
- 部分安全测试使用源码字符串断言，建议后续补 TestClient 集成测试

### 覆盖与未覆盖

- 已覆盖：auth/tenant/alert/notify/rule/escalation/core 主路径 + 前端契约页面
- 未深度覆盖：云 adapter payload 逐行、AI provider SSRF 全文、Alembic 数据迁移、部署配置、E2E

## [S1] Problem

SentinelX 前后端分别用 FastAPI Pydantic schema 与 TypeScript interface/Zod 描述 API 契约，缺少共享类型源。历史上已出现过 `tenant_id` 类型不一致等问题。需要系统审计：

1. 前后端数据类型/字段/枚举是否一致
2. 逻辑 bug、边界与错误处理缺陷
3. 安全与数据正确性风险（多租户隔离、权限、注入等）
4. 性能与可维护性优化点

并在审计后实施可安全落地的关键修复与优化。

## [S2] Design

### 审计范围

- Backend: `backend/apps/**`（alert/auth/notify/rule/tenant/ai/escalation/maintenance/callback/core）
- Frontend: `frontend/src/**`（types/schemas/services/pages/components/stores/hooks）
- API 边界: `backend/apps/*/schemas.py` + routers 响应模型 vs `frontend/src/types/**` + `frontend/src/services/api.ts` 调用方
- 既有文档: `docs/API.md`（对照实际实现，而非作为权威）

### 方法

1. **契约对照**：枚举 GET/POST 端点，比对请求/响应字段名、类型（int/str/float/bool/Optional/list/dict）、时间格式、分页结构、枚举值
2. **正确性扫描**：租户过滤是否贯穿、权限装饰器、并发/事务、异常吞掉、状态机漏洞
3. **性能扫描**：N+1、缺索引、全表扫描、重复计算、前端无谓重渲染/大列表
4. **产出分级**：Critical / High / Medium / Low / Info

### 修复策略

- **Critical + High**：本轮实施修复（类型不一致导致运行时错误、租户越权、数据损坏风险、明确逻辑 bug）
- **Medium**：实施低风险、收益明确的修复与优化
- **Low / Info**：写入报告，本轮不改（除非改动极小且无行为风险）
- 修复优先：保持 API 向后兼容；确需破坏性变更时前后端同步改并在报告记录

### 验证边界

- Backend: `pytest`（tests/）
- Frontend: `tsc --noEmit` / `npm run build`（若环境可用）
- 不新增 E2E；不依赖外部云 API

## [S3] Out of Scope

- 大规模架构重写、换框架
- 引入 OpenAPI codegen / monorepo 类型共享流水线（仅作为建议写入报告）
- UI/UX 重设计
- 未在仓库中运行的部署拓扑变更
- 对第三方适配器 payload 的完整回归（仅静态审查）

## Tasks

- [x] T1: 类型一致性审计 — acceptance: 产出前后端字段/类型/枚举差异清单，含文件:行号证据 (covers: S2)
- [x] T2: 安全与正确性审计 — acceptance: 产出 Critical/High 问题清单，含复现路径或代码证据 (covers: S2)
- [x] T3: 性能与可维护性审计 — acceptance: 产出优化点清单，按收益/风险排序 (covers: S2)
- [x] T4: 实施 Critical/High 与低风险 Medium 修复 — acceptance: 对应问题在代码中已修复，关键路径有回归测试或可验证行为 (covers: S2; depends: T1,T2,T3)
- [x] T5: 仓库验证 — acceptance: pytest 与前端 typecheck/build 通过或标注 PRE-EXISTING (covers: S2; depends: T4)
- [x] T6: 独立 Review — acceptance: reviewer 对 spec 合规/正确性/一致性给出结论，critical 已闭环 (covers: S2; depends: T5)
- [x] T7: Finalize 报告 — acceptance: 本文件 status=delivered，Report 含完整发现与验证记录 (covers: S1,S2; depends: T6)
