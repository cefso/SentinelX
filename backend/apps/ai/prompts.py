"""
SentinelX - AI 功能默认 System Prompt
"""
from typing import Dict, List, Optional, Any

PROMPT_KEYS = ("analyze", "polish", "suggest_actions", "predict_impact")

PROMPT_META: List[Dict[str, str]] = [
    {
        "key": "analyze",
        "title": "根因分析",
        "description": "分析告警可能原因与处理建议，输出 Markdown 结构",
    },
    {
        "key": "polish",
        "title": "内容润色",
        "description": "将告警润色为通知文案。可使用占位符 {{style_instruction}}",
    },
    {
        "key": "suggest_actions",
        "title": "建议操作",
        "description": "推荐可执行的排查与处置步骤，Markdown 列表输出",
    },
    {
        "key": "predict_impact",
        "title": "影响预测",
        "description": "预测告警未处理时的业务与服务影响",
    },
]

DEFAULT_PROMPTS: Dict[str, str] = {
    "analyze": """你是一个资深的SRE工程师，擅长分析告警的根本原因。
请根据提供的告警信息，分析可能的根本原因，并给出处理建议。
请用中文回复，格式如下：

## 可能原因
1. ...
2. ...
3. ...

## 处理建议
1. ...
2. ...
3. ...

## 进一步调查
- 检查哪些指标...
- 查看哪些日志...
""",
    "polish": """你是一个告警通知撰写专家。请将告警信息润色成一段简洁、清晰的通知文本。

要求:
- {style_instruction}
- 突出关键信息（告警名称、严重级别、发生时间）
- 如有必要，添加简要的上下文信息
- 长度控制在200字以内
- 可使用少量表情符号增加可读性
""",
    "suggest_actions": """你是一个SRE告警处理专家。请根据告警历史和当前告警，推荐下一步应该执行的操作。

要求:
- 只输出 3-5 条具体、可执行的操作建议（检查、排查、止血、通知、升级等）
- 按优先级从高到低排序
- 每条建议一句话，说明「做什么」，不要解释告警是什么
- 严禁复述告警字段（不要写标题、来源、严重级别、状态、内容、触发时间等元数据）
- 如果是重复告警，优先建议升级或通知相关人员

输出格式（严格遵守）:
- 使用 Markdown 撰写，建议用无序列表（每条以 "- " 开头）
- 不要输出与建议无关的前言或总结
""",
    "predict_impact": """你是一个SRE工程师。请分析这个告警如果不处理，可能造成的影响。

要求:
- 预测可能的服务影响范围
- 评估业务影响程度
- 给出影响持续时间预估
- 用非技术人员也能理解的语言描述
- 使用 Markdown 组织内容
""",
}

STYLE_INSTRUCTIONS = {
    "formal": "正式、简洁、专业",
    "simple": "简洁、易懂",
    "friendly": "简洁、易懂、友好",
}


def get_default_prompt(key: str) -> str:
    if key not in DEFAULT_PROMPTS:
        raise KeyError(f"Unknown prompt key: {key}")
    return DEFAULT_PROMPTS[key]


def resolve_system_prompt(
    key: str,
    custom_prompts: Optional[Dict[str, Any]] = None,
    **format_kwargs: str,
) -> str:
    """取租户自定义或默认 System Prompt，并替换占位符"""
    custom = (custom_prompts or {}).get(key) if custom_prompts else None
    template = (custom.strip() if isinstance(custom, str) and custom.strip() else None) or get_default_prompt(key)
    try:
        return template.format(**format_kwargs)
    except KeyError:
        return template


def normalize_prompts_for_save(prompts: Optional[Dict[str, Optional[str]]]) -> Dict[str, str]:
    """仅保存与默认不同的提示词，空字符串表示清除自定义"""
    if not prompts:
        return {}
    stored: Dict[str, str] = {}
    for key in PROMPT_KEYS:
        if key not in prompts:
            continue
        value = prompts[key]
        if value is None:
            continue
        trimmed = value.strip()
        if not trimmed:
            continue
        if trimmed == get_default_prompt(key).strip():
            continue
        if len(trimmed) > 8000:
            trimmed = trimmed[:8000]
        stored[key] = trimmed
    return stored


def prompts_for_response(ai_blob: dict) -> Dict[str, Optional[str]]:
    """API 响应：各模块当前生效的 system prompt（含默认）"""
    custom = ai_blob.get("prompts") if isinstance(ai_blob.get("prompts"), dict) else {}
    result: Dict[str, Optional[str]] = {}
    for key in PROMPT_KEYS:
        c = custom.get(key)
        if isinstance(c, str) and c.strip():
            result[key] = c.strip()
        else:
            result[key] = get_default_prompt(key)
    return result


def custom_prompts_from_blob(ai_blob: dict) -> Dict[str, str]:
    raw = ai_blob.get("prompts")
    if not isinstance(raw, dict):
        return {}
    return {k: v.strip() for k, v in raw.items() if k in PROMPT_KEYS and isinstance(v, str) and v.strip()}
