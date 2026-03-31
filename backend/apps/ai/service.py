"""
SentinelX - AI服务
根因分析、内容润色等AI功能
"""
from typing import Optional, Dict, Any, List
import structlog

from apps.ai.client import LLMFactory
from apps.alert.models import Alert

logger = structlog.get_logger()


class AIService:
    """AI服务"""

    def __init__(
        self,
        provider: str = "openai",
        api_key: str = None,
        model: str = None,
    ):
        self.client = LLMFactory.create_client(provider, api_key, model)

    async def analyze_root_cause(self, alert: Alert) -> tuple[Optional[str], Optional[str]]:
        """
        根因分析
        分析告警的可能原因并提供处理建议
        """
        # 构建提示词
        system_prompt = """你是一个资深的SRE工程师，擅长分析告警的根本原因。
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
"""

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
        """
        内容润色
        将告警内容润色成更易读的通知格式
        """
        if template:
            # 使用模板格式化
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

        # 构建润色提示词
        system_prompt = f"""你是一个告警通知撰写专家。请将告警信息润色成一段简洁、清晰的通知文本。

要求:
- {style == 'formal' and '正式、简洁、专业' or '简洁、易懂、友好'}
- 突出关键信息（告警名称、严重级别、发生时间）
- 如有必要，添加简要的上下文信息
- 长度控制在200字以内
- 使用表情符号增加可读性
"""

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
    ) -> tuple[Optional[List[str]], Optional[str]]:
        """
        建议操作
        根据告警历史和当前告警，推荐下一步操作
        """
        system_prompt = """你是一个SRE告警处理专家。请根据告警历史和当前告警，推荐下一步应该执行的操作。

要求:
- 给出3-5个具体、可执行的操作建议
- 按优先级排序
- 每个建议简明扼要
- 如果是重复告警，优先建议升级或通知相关人员
"""

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

            # 解析返回的建议
            actions = []
            for line in result.split("\n"):
                line = line.strip()
                if line and (line.startswith("-") or line.startswith("*") or line[0].isdigit()):
                    # 移除列表标记
                    cleaned = line.lstrip("-*0123456789. )").strip()
                    if cleaned:
                        actions.append(cleaned)

            logger.info("suggest_actions_success", alert_id=alert.id, action_count=len(actions))
            return actions if actions else None, None

        except Exception as e:
            logger.error("suggest_actions_exception", alert_id=alert.id, error=str(e))
            return None, str(e)

    async def predict_impact(
        self,
        alert: Alert,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        影响预测
        预测该告警如果未处理可能造成的影响
        """
        system_prompt = """你是一个SRE工程师。请分析这个告警如果不处理，可能造成的影响。

要求:
- 预测可能的服务影响范围
- 评估业务影响程度
- 给出影响持续时间预估
- 用非技术人员也能理解的语言描述
"""

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
