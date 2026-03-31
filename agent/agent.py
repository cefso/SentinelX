"""
SentinelX - 内网Agent
用于收集内网服务指标和告警
"""
import asyncio
import json
import logging
import os
import socket
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent配置"""
    api_base_url: str = "http://localhost:8000/api/v1"
    api_key: str = ""
    tenant_id: str = ""
    agent_id: str = str(uuid.uuid4())[:8]
    hostname: str = socket.gethostname()
    tags: Dict[str, str] = field(default_factory=dict)
    heartbeat_interval: int = 30  # 秒
    metrics_interval: int = 60  # 秒
    retry_attempts: int = 3
    retry_delay: int = 5


class SentinelXAgent:
    """SentinelX Agent"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.running = False
        self.client = httpx.AsyncClient(timeout=30)

    async def start(self):
        """启动Agent"""
        self.running = True
        logger.info(f"SentinelX Agent {self.config.agent_id} starting...")

        # 注册Agent
        await self.register()

        # 启动心跳
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # 启动指标收集
        metrics_task = asyncio.create_task(self._metrics_loop())

        # 启动命令监听
        command_task = asyncio.create_task(self._command_loop())

        try:
            await asyncio.gather(heartbeat_task, metrics_task, command_task)
        except asyncio.CancelledError:
            logger.info("Agent tasks cancelled")
        finally:
            await self.stop()

    async def stop(self):
        """停止Agent"""
        self.running = False
        await self.client.aclose()
        logger.info("SentinelX Agent stopped")

    async def register(self) -> bool:
        """注册Agent到平台"""
        payload = {
            "agent_id": self.config.agent_id,
            "hostname": self.config.hostname,
            "ip_address": self._get_ip_address(),
            "tags": self.config.tags,
            "version": "1.0.0",
        }

        for attempt in range(self.config.retry_attempts):
            try:
                response = await self.client.post(
                    f"{self.config.api_base_url}/agent/register",
                    json=payload,
                    headers={"X-API-Key": self.config.api_key},
                )
                if response.status_code == 200:
                    logger.info(f"Agent registered successfully: {self.config.agent_id}")
                    return True
                else:
                    logger.warning(f"Agent registration failed: {response.status_code}")
            except Exception as e:
                logger.error(f"Agent registration error (attempt {attempt + 1}): {e}")

            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(self.config.retry_delay)

        return False

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            await asyncio.sleep(self.config.heartbeat_interval)

    async def _send_heartbeat(self):
        """发送心跳"""
        payload = {
            "agent_id": self.config.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "online",
            "cpu_percent": self._get_cpu_percent(),
            "memory_percent": self._get_memory_percent(),
        }

        response = await self.client.post(
            f"{self.config.api_base_url}/agent/heartbeat",
            json=payload,
            headers={"X-API-Key": self.config.api_key},
        )

        if response.status_code == 200:
            logger.debug("Heartbeat sent successfully")
        else:
            logger.warning(f"Heartbeat failed: {response.status_code}")

    async def _metrics_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                await self._collect_and_send_metrics()
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")

            await asyncio.sleep(self.config.metrics_interval)

    async def _collect_and_send_metrics(self):
        """收集并发送指标"""
        metrics = self._collect_system_metrics()

        payload = {
            "agent_id": self.config.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
        }

        response = await self.client.post(
            f"{self.config.api_base_url}/agent/metrics",
            json=payload,
            headers={"X-API-Key": self.config.api_key},
        )

        if response.status_code == 200:
            logger.debug(f"Metrics sent successfully: {len(metrics)} metrics")
        else:
            logger.warning(f"Metrics sending failed: {response.status_code}")

    async def _command_loop(self):
        """命令监听循环"""
        while self.running:
            try:
                await self._poll_commands()
            except Exception as e:
                logger.error(f"Command polling error: {e}")

            await asyncio.sleep(10)

    async def _poll_commands(self):
        """轮询待执行的命令"""
        response = await self.client.get(
            f"{self.config.api_base_url}/agent/{self.config.agent_id}/commands",
            headers={"X-API-Key": self.config.api_key},
        )

        if response.status_code == 200:
            commands = response.json().get("commands", [])
            for command in commands:
                await self._execute_command(command)
        else:
            logger.warning(f"Command polling failed: {response.status_code}")

    async def _execute_command(self, command: Dict[str, Any]):
        """执行命令"""
        cmd_id = command.get("id")
        cmd_type = command.get("type")
        cmd_params = command.get("params", {})

        logger.info(f"Executing command {cmd_id}: {cmd_type}")

        result = {"id": cmd_id, "status": "success", "output": ""}

        try:
            if cmd_type == "shell":
                result["output"] = await self._execute_shell(cmd_params.get("command", ""))
            elif cmd_type == "health_check":
                result["output"] = self._health_check()
            elif cmd_type == "collect_logs":
                result["output"] = await self._collect_logs(cmd_params)
            else:
                result["status"] = "error"
                result["output"] = f"Unknown command type: {cmd_type}"
        except Exception as e:
            result["status"] = "error"
            result["output"] = str(e)

        # 上报命令结果
        await self._report_command_result(result)

    async def _execute_shell(self, command: str) -> str:
        """执行Shell命令"""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (stdout + stderr).decode()

    def _health_check(self) -> str:
        """健康检查"""
        return json.dumps({
            "status": "healthy",
            "agent_id": self.config.agent_id,
            "hostname": self.config.hostname,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def _collect_logs(self, params: Dict) -> str:
        """收集日志"""
        # 简化实现
        return "Log collection not implemented"

    async def _report_command_result(self, result: Dict):
        """上报命令执行结果"""
        try:
            await self.client.post(
                f"{self.config.api_base_url}/agent/commands/{result['id']}/result",
                json=result,
                headers={"X-API-Key": self.config.api_key},
            )
        except Exception as e:
            logger.error(f"Failed to report command result: {e}")

    def _collect_system_metrics(self) -> List[Dict]:
        """收集系统指标"""
        # 这里可以扩展更多指标
        return [
            {
                "name": "system.cpu.usage",
                "value": self._get_cpu_percent(),
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "name": "system.memory.usage",
                "value": self._get_memory_percent(),
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "name": "system.disk.usage",
                "value": self._get_disk_usage(),
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]

    def _get_ip_address(self) -> str:
        """获取IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _get_cpu_percent(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0

    def _get_memory_percent(self) -> float:
        """获取内存使用率"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0

    def _get_disk_usage(self) -> float:
        """获取磁盘使用率"""
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            return 0.0


async def main():
    """主函数"""
    config = AgentConfig(
        api_base_url=os.getenv("SENTINELX_API_URL", "http://localhost:8000/api/v1"),
        api_key=os.getenv("SENTINELX_API_KEY", ""),
        tenant_id=os.getenv("SENTINELX_TENANT_ID", ""),
        tags=json.loads(os.getenv("SENTINELX_TAGS", "{}")),
    )

    agent = SentinelXAgent(config)
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
