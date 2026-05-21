"""
SentinelX - AI服务
根因分析、内容润色等AI功能
"""
from typing import Optional, Dict, Any, List
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ai.client import ProviderRegistry
from apps.ai.config import resolve_tenant_ai_config, TenantAIConfig
from apps.ai.prompts import resolve_system_prompt, STYLE_INSTRUCTIONS
from apps.alert.models import Alert

logger = structlog.get_logger()


async def build_ai_service(db: AsyncSession, tenant_id: int) -> "AIService":
    """从租户配置构建 AI 服务"""
    cfg = await resolve_tenant_ai_config(db, tenant_id)
    return AIService.from_tenant_config(cfg)


class AIService:
    """AI服务"""

    def __init__(self, client, system_prompts: Optional[Dict[str, str]] = None):
        self.client = client
        self.system_prompts = system_prompts or {}

    @classmethod
    def from_tenant_config(cls, cfg: TenantAIConfig) -> "AIService":
        client = ProviderRegistry.create_client(
            provider_id=cfg.provider_id,
            api_key=cfg.api_key,
            model=cfg.model,
            base_url=cfg.base_url,
        )
        return cls(client, system_prompts=cfg.prompts)

    async def analyze_root_cause(self, alert: Alert) -> tuple[Optional[str], Optional[str]]:
        """根因分析"""
        system_prompt = resolve_system_prompt("analyze", self.system_prompts)

        prompt = f"""## 告警信息
- 标题: {alert.title}
- 告警来源: {alert.source}
- 严重级别: {alert.severity}
- 状态: {alert.status}
- 内容: {alert.content or '无'}
- 触发时间: {alert.fired_at}
- 触发次数: {alert.fire_count}
- 标签: {alert.labels or {}}
- 指标: {alert.metric_name or '无'}
- 指标值: {alert.metric_value or '无'}
"""

        try:
            result, error = await self.client.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.5,
                max_tokens=1500,
            )

            if error:
                logger.error("root_cause_analysis_error", alert_id=alert.id, error=error)
                return None, error

            logger.info("root_cause_analysis_success", alert_id=alert.id)
            return result, None

        except Exception as e:
            logger.error("root_cause_analysis_exception", alert_id=alert.id, error=str(e))
            return None, str(e)

    async def polish_content(
        self,
        alert: Alert,
        template: str = None,
        style: str = "formal",
    ) -> tuple[Optional[str], Optional[str]]:
        """内容润色"""
        if template:
            content = template
            replacements = {
                "{{title}}": alert.title or "",
                "{{content}}": alert.content or "",
                "{{severity}}": alert.severity or "",
                "{{source}}": alert.source or "",
                "{{fired_at}}": str(alert.fired_at) if alert.fired_at else "",
                "{{fire_count}}": str(alert.fire_count),
            }
            if alert.labels:
                for key, value in alert.labels.items():
                    replacements[f"{{{{labels.{key}}}}}"] = str(value)

            for key, value in replacements.items():
                content = content.replace(key, value)

            return content, None

        style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["formal"])
        system_prompt = resolve_system_prompt(
            "polish",
            self.system_prompts,
            style_instruction=style_instruction,
        )

        prompt = f"""## 原始告警信息
- 标题: {alert.title}
- 告警来源: {alert.source}
- 严重级别: {alert.severity}
- 状态: {alert.status}
- 内容: {alert.content or '无'}
- 触发时间: {alert.fired_at}
- 触发次数: {alert.fire_count}
- 标签: {alert.labels or {}}
- 指标: {alert.metric_name or '无'}
- 指标值: {alert.metric_value or '无'}

请生成一段简洁的通知文本。
"""

        try:
            result, error = await self.client.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.7,
                max_tokens=500,
            )

            if error:
                logger.error("content_polish_error", alert_id=alert.id, error=error)
                return None, error

            logger.info("content_polish_success", alert_id=alert.id)
            return result, None

        except Exception as e:
            logger.error("content_polish_exception", alert_id=alert.id, error=str(e))
            return None, str(e)

    async def suggest_actions(
        self,
        alert: Alert,
        history: List[Dict[str, Any]] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """建议操作"""
        system_prompt = resolve_system_prompt("suggest_actions", self.system_prompts)

        history_text = ""
        if history and len(history) > 0:
            history_text = "## 最近类似的告警历史\n"
            for i, h in enumerate(history[:5]):
                history_text += f"{i+1}. {h.get('title', 'Unknown')} - {h.get('resolved_at', '未解决')}\n"

        prompt = f"""## 当前告警
- 标题: {alert.title}
- 告警来源: {alert.source}
- 严重级别: {alert.severity}
- 状态: {alert.status}
- 内容: {alert.content or '无'}
- 触发时间: {alert.fired_at}
- 触发次数: {alert.fire_count}
- 标签: {alert.labels or {}}

{history_text}

请给出具体的操作建议。
"""

        try:
            result, error = await self.client.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.5,
                max_tokens=1000,
            )

            if error:
                logger.error("suggest_actions_error", alert_id=alert.id, error=error)
                return None, error

            text = (result or "").strip()
            logger.info("suggest_actions_success", alert_id=alert.id, content_len=len(text))
            return text or None, None

        except Exception as e:
            logger.error("suggest_actions_exception", alert_id=alert.id, error=str(e))
            return None, str(e)

    async def predict_impact(
        self,
        alert: Alert,
    ) -> tuple[Optional[str], Optional[str]]:
        """影响预测"""
        system_prompt = resolve_system_prompt("predict_impact", self.system_prompts)

        prompt = f"""## 告警信息
- 标题: {alert.title}
- 告警来源: {alert.source}
- 严重级别: {alert.severity}
- 内容: {alert.content or '无'}
- 标签: {alert.labels or {}}
- 指标: {alert.metric_name or '无'}
- 指标值: {alert.metric_value or '无'}
- 触发时间: {alert.fired_at}
- 触发次数: {alert.fire_count}

请分析如果这个告警不处理，可能造成的影响。
"""

        try:
            result, error = await self.client.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=0.5,
                max_tokens=800,
            )

            if error:
                logger.error("predict_impact_error", alert_id=alert.id, error=error)
                return None, error

            logger.info("predict_impact_success", alert_id=alert.id)
            return result, None

        except Exception as e:
            logger.error("predict_impact_exception", alert_id=alert.id, error=str(e))
            return None, str(e)
