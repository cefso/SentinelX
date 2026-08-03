"""
SentinelX - 阿里云语音通知渠道
"""
import json
import structlog
from typing import Dict, Any, Optional, Tuple

from .base import NotificationChannel

logger = structlog.get_logger()


class AliyunVoiceChannel(NotificationChannel):
    """阿里云语音通知渠道（dyvmsapi - SingleCallByTts）"""

    channel_type = "aliyun_voice"

    def _build_tts_param(self, alert: Any, custom_template: Dict[str, str] = None) -> str:
        """
        构建 TTS 模板参数 JSON 字符串。
        custom_template: { "模板变量名": "alert字段名" } 映射
        """
        if custom_template:
            # 用户自定义映射：key=模板变量名, value=alert字段名
            params = {}
            for tpl_var, field_name in custom_template.items():
                value = getattr(alert, field_name, None)
                params[tpl_var] = str(value) if value is not None else ""
            return json.dumps(params, ensure_ascii=False)

        # 默认映射
        params = {
            "alert_severity": getattr(alert, "severity", "unknown"),
            "alert_info": getattr(alert, "title", "") or getattr(alert, "content", ""),
        }
        return json.dumps(params, ensure_ascii=False)

    async def send(self, alert: Any, template: str = None) -> Tuple[bool, Optional[str]]:
        """发送语音通知"""
        try:
            from alibabacloud_dyvmsapi20170525.client import Client as DyvmsapiClient
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_dyvmsapi20170525 import models as dyvmsapi_models
            from alibabacloud_tea_util import models as util_models
        except ImportError:
            return False, "alibabacloud_dyvmsapi20170525 SDK 未安装，请运行: pip install alibabacloud_dyvmsapi20170525==5.3.0"

        # 构建 TTS 参数
        custom_template = self.config.get("tts_param_template")
        tts_param = self._build_tts_param(alert, custom_template)

        # 初始化客户端
        try:
            config = open_api_models.Config(
                access_key_id=self.config["access_key_id"],
                access_key_secret=self.config["access_key_secret"],
            )
            config.endpoint = "dyvmsapi.aliyuncs.com"
            client = DyvmsapiClient(config)
        except Exception as e:
            return False, f"初始化阿里云客户端失败: {str(e)}"

        # 解析被叫号码列表
        called_numbers = [n.strip() for n in self.config["called_number"].split(",") if n.strip()]
        if not called_numbers:
            return False, "未配置被叫号码"

        template_code = self.config["template_code"]
        runtime = util_models.RuntimeOptions()

        # 依次遍历每个号码调用
        success_count = 0
        last_error = None

        for phone_num in called_numbers:
            try:
                request = dyvmsapi_models.SingleCallByTtsRequest(
                    called_number=phone_num,
                    tts_code=template_code,
                    tts_param=tts_param,
                )
                response = client.single_call_by_tts_with_options(request, runtime)
                result = response.body.to_map()

                if result.get("Code") == "OK":
                    success_count += 1
                    logger.info("aliyun_voice_sent", phone=phone_num, alert_id=getattr(alert, "id", None))
                else:
                    last_error = f"号码 {phone_num} 发送失败: Code={result.get('Code')}, Message={result.get('Message')}"
                    logger.warning("aliyun_voice_failed", phone=phone_num, code=result.get("Code"), message=result.get("Message"))

            except Exception as e:
                last_error = f"号码 {phone_num} 异常: {str(e)}"
                logger.error("aliyun_voice_error", phone=phone_num, error=str(e))

        if success_count > 0:
            return True, None
        return False, last_error or "所有号码发送失败"

    def get_default_template(self) -> str:
        """默认消息模板（语音参数格式）"""
        return '{"alert_severity": "{{ severity }}", "alert_info": "{{ title }}"}'
