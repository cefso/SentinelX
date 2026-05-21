"""
SentinelX - AI 提示词测试
"""
from apps.ai.prompts import (
    resolve_system_prompt,
    normalize_prompts_for_save,
    get_default_prompt,
    DEFAULT_PROMPTS,
)


def test_resolve_uses_default():
    text = resolve_system_prompt("analyze", {})
    assert text == DEFAULT_PROMPTS["analyze"]


def test_resolve_uses_custom():
    custom = {"analyze": "自定义根因分析提示"}
    assert resolve_system_prompt("analyze", custom) == "自定义根因分析提示"


def test_polish_style_placeholder():
    text = resolve_system_prompt(
        "polish",
        {},
        style_instruction="正式、简洁、专业",
    )
    assert "正式、简洁、专业" in text
    assert "{{style_instruction}}" not in text


def test_normalize_only_stores_diff():
    default = get_default_prompt("analyze")
    stored = normalize_prompts_for_save({
        "analyze": default,
        "polish": "完全自定义的润色提示词内容",
    })
    assert "analyze" not in stored
    assert "polish" in stored
