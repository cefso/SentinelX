"""
SentinelX - 公共工具函数
跨模块共享的工具函数（不依赖任何外部模块，仅使用标准库）
"""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional


# ============ 指纹生成 ============
def generate_fingerprint(
    source: str,
    alert_key: str,
    labels: Optional[dict[str, Any]] = None,
    algorithm: str = "sha256",
    length: int = 16,
) -> str:
    """
    生成告警指纹，用于去重判断

    Args:
        source: 告警来源，如 prometheus、aliyun
        alert_key: 告警唯一标识，通常是 metric_name 或规则名
        labels: 告警标签，用于区分同来源同类型的不同告警
        algorithm: 哈希算法 (sha256/md5)
        length: 返回的指纹长度

    Returns:
        十六进制格式的指纹字符串

    Example:
        >>> generate_fingerprint("prometheus", "HighCPUUsage", {"cluster": "prod"})
        'a1b2c3d4e5f67890'
    """
    fp_data = {
        "source": source,
        "alert_key": alert_key,
        "labels": json.dumps(labels or {}, sort_keys=True),
    }
    fp_str = json.dumps(fp_data, sort_keys=True)

    if algorithm == "md5":
        digest = hashlib.md5(fp_str.encode()).hexdigest()
    else:
        digest = hashlib.sha256(fp_str.encode()).hexdigest()

    return digest[:length]


def generate_alert_key(
    metric_name: str,
    labels: Optional[dict[str, Any]] = None,
) -> str:
    """
    生成告警唯一标识 key

    Example:
        >>> generate_alert_key("cpu_usage", {"host": "server-01"})
        'cpu_usage:host=server-01'
    """
    parts = [metric_name]
    if labels:
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        parts.append(label_str)
    return ":".join(parts)


# ============ 时间处理 ============
def get_timestamp() -> str:
    """获取当前 UTC 时间，ISO 8601 格式（带毫秒）"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_unix_timestamp() -> int:
    """获取当前 Unix 时间戳（秒）"""
    return int(time.time())


def parse_iso_timestamp(ts: str) -> datetime:
    """解析 ISO 8601 时间字符串为 datetime 对象"""
    ts = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


def format_duration_ms(ms: int) -> str:
    """格式化毫秒为人类可读时长"""
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


# ============ 字符串处理 ============
def truncate_string(s: str, max_length: int = 512, suffix: str = "...") -> str:
    """
    截断过长的字符串

    Args:
        s: 原始字符串
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的字符串
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def mask_sensitive(s: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """
    遮蔽敏感字符串，只显示前 N 个字符

    Args:
        s: 原始字符串
        visible_chars: 保留的可显示字符数
        mask_char: 遮蔽字符

    Example:
        >>> mask_sensitive("sk-ant-abc123xyz")
        'sk-ant-****************************xyz'
    """
    if len(s) <= visible_chars * 2:
        return mask_char * len(s)
    prefix = s[:visible_chars]
    suffix = s[-visible_chars:]
    mask_length = len(s) - visible_chars * 2
    return f"{prefix}{mask_char * mask_length}{suffix}"


def mask_api_key(api_key: str) -> str:
    """
    遮蔽 API Key，只显示前缀和后缀

    Example:
        >>> mask_api_key("sxw_v1_abc123xyz789")
        'sxw_v1_***xyz789'
    """
    if len(api_key) <= 12:
        return mask_char := "*" * len(api_key)

    # 保留前缀 sxw_v1_xxx 部分
    prefix_match = re.match(r"^(sx[wsa]?_v1_\w+)", api_key)
    if prefix_match:
        prefix = prefix_match.group(1)
        suffix = api_key[-6:] if len(api_key) > 10 else ""
        if len(api_key) > len(prefix) + len(suffix) + 3:
            return f"{prefix}_***{suffix}"
        return mask_sensitive(api_key, 4)

    return mask_sensitive(api_key, 4)


# ============ 标签处理 ============
def parse_labels(raw: Any) -> dict[str, str]:
    """
    解析各种格式的标签数据为标准 dict[str, str]

    支持格式:
    - dict: {"key": "value"}
    - str: '{"key": "value"}' 或 'key=value,key2=value2'
    - list: [{"key": "value"}] 或 ["key=value"]
    """
    if not raw:
        return {}

    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}

    if isinstance(raw, str):
        # 尝试 JSON 解析
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试 key=value,key2=value2 格式
        labels: dict[str, str] = {}
        for part in raw.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                labels[k.strip()] = v.strip()
        return labels

    if isinstance(raw, list):
        result: dict[str, str] = {}
        for item in raw:
            if isinstance(item, dict):
                result.update({str(k): str(v) for k, v in item.items()})
            elif isinstance(item, str) and "=" in item:
                k, v = item.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    return {}


def labels_to_filter_string(labels: dict[str, str]) -> str:
    """将标签字典转换为过滤字符串"""
    return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))


# ============ 正则处理 ============
def safe_regex_match(pattern: str, text: str, flags: int = 0) -> bool:
    """
    安全地执行正则匹配，捕获异常

    Returns:
        True 如果匹配成功，False 否则（包括异常）
    """
    try:
        return bool(re.search(pattern, text, flags))
    except re.error:
        return False


# ============ 数值处理 ============
def clamp(value: float, min_val: float, max_val: float) -> float:
    """将数值限制在指定范围内"""
    return max(min_val, min(max_val, value))


def parse_percentage(s: str | float) -> float:
    """解析百分比字符串或数值"""
    if isinstance(s, (int, float)):
        return float(s)
    s = s.strip().rstrip("%")
    return float(s) / 100.0 if "%" in str(s) else float(s)
