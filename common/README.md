# SentinelX - Common 共享模块

后端（backend/）、Agent（agent/）以及工具脚本共享的代码模块。

## 目录结构

```
common/
├── __init__.py    # 模块入口，导出主要 API
├── constants.py   # 共享常量（告警级别、状态、来源类型等）
├── types.py       # Pydantic 类型定义（供 Agent 和后端共用）
└── utils.py       # 工具函数（指纹生成、时间处理、字符串处理等）
```

## 使用方式

### 后端使用

```python
from common.constants import AlertSeverity, AlertStatus
from common.utils import generate_fingerprint, get_timestamp
from common.types import HeartbeatPayload
```

### Agent 使用

```python
import sys
sys.path.insert(0, "/path/to/SentinelX")

from common.constants import AlertSeverity
from common.utils import generate_fingerprint, get_timestamp
```

### 依赖说明

`common/` 模块**仅依赖 Python 标准库**，不引入任何第三方依赖，确保 Agent 等轻量级客户端可以无障碍使用。

### 类型定义

`types.py` 中的 Pydantic 模型用于标准化前后端通信的数据结构，包括：

| 类型 | 说明 |
|------|------|
| `HeartbeatPayload` | Agent 心跳数据 |
| `MetricsPayload` | Agent 指标上报数据 |
| `CommandRequest` | 平台下发命令 |
| `CommandResult` | 命令执行结果 |
| `AgentRegistration` | Agent 注册信息 |

### 常量

| 常量类 | 说明 |
|--------|------|
| `AlertSeverity` | CRITICAL/HIGH/MEDIUM/LOW/INFO |
| `AlertStatus` | FIRING/RESOLVED/ACKNOWLEDGED/SILENCED |
| `AlertSourceType` | prometheus/aliyun/tencent/custom/agent 等 |
| `NotificationChannelType` | dingtalk/feishu/wecom/email 等 |
| `RuleConditionOperator` | eq/ne/gt/contains/regex 等 |

### 工具函数

| 函数 | 说明 |
|------|------|
| `generate_fingerprint` | 生成告警指纹，用于去重 |
| `get_timestamp` | 获取 ISO 8601 格式时间戳 |
| `parse_labels` | 解析多种格式的标签数据 |
| `mask_sensitive` | 遮蔽敏感字符串 |
| `safe_regex_match` | 安全正则匹配 |
| `clamp` | 限制数值范围 |
