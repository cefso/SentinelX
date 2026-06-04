"""
抑制规则生效窗口：从规则保存时刻起算 duration_minutes。
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


def compute_suppress_effective_until(duration_minutes: int) -> Optional[str]:
    """计算抑制窗口截止时间（ISO8601 UTC）。duration_minutes=0 表示永久抑制。"""
    if duration_minutes <= 0:
        return None
    until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
    return until.isoformat()


def enrich_suppress_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """写入 duration_minutes 与 effective_until（创建/更新抑制规则时调用）。"""
    merged = dict(config or {})
    duration = int(merged.get("duration_minutes") or 0)
    merged["duration_minutes"] = duration
    merged["effective_until"] = compute_suppress_effective_until(duration)
    if merged.get("enabled") is None:
        merged["enabled"] = True
    if not merged.get("type"):
        merged["type"] = "rule_based"
    return merged


def parse_effective_until(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_suppress_rule_in_effect(
    suppress_config: Dict[str, Any],
    now: Optional[datetime] = None,
    *,
    rule_created_at: Optional[datetime] = None,
) -> tuple[bool, str]:
    """
    判断抑制规则是否在生效窗口内。
    返回 (是否生效, 说明)。
    """
    now = now or datetime.now(timezone.utc)
    duration = int(suppress_config.get("duration_minutes") or 0)
    if duration <= 0:
        return True, "永久抑制"

    until = parse_effective_until(suppress_config.get("effective_until"))
    if until is None and rule_created_at is not None:
        created = rule_created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        until = created + timedelta(minutes=duration)

    if until is None:
        return True, "抑制窗口（未设置截止时间，按永久处理）"

    if now < until:
        return True, f"抑制窗口至 {until.isoformat()}"

    return False, "抑制规则已过期"
