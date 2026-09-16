"""lcmdb 适配器解析测试，重点覆盖 alert_key 超长场景"""
import pytest

from apps.alert.adapters.lcmdb import (
    LcmdbAdapter,
    MAX_ALERT_KEY_LENGTH,
    _clamp_alert_key,
    _extract_short_name,
)


PROCESS_CMD = (
    "java -javaagent:/opt/skywalking-agent/skywalking-agent.jar "
    "-Dskywalking.agent.service_name=主数据平台-数据-fd "
    "-Xms512M -Xmx10G -jar jar/foundation-api.jar "
    "--spring.config.location=config/application-fd.yaml "
    "--spring.profiles.active=fd --server.port=11090"
)


def _raw_alert(text: str) -> dict:
    return {
        "msgtype": "markdown",
        "markdown": {"title": "告警通知", "text": text},
    }


@pytest.mark.asyncio
async def test_parse_process_alert_with_long_command_does_not_exceed_limit():
    adapter = LcmdbAdapter()
    text = (
        "告警编号：568610\n"
        f"告警对象：主数据管理平台-生产环境-App服务器1 的 [进程:{PROCESS_CMD}]\n"
        "设备ID：1277\n"
        "当前:运行数=[0];\n"
        "阈值:[运行数<1]\n"
        "当前状态：<font color='red'>错误</font>\n"
        "IP地址：172.16.11.196\n"
        "持续时间：9秒\n"
        "设备类型：CentOS\n"
        "开始时间：2026-08-27 20:15:00"
    )
    alert = await adapter.parse(_raw_alert(text), "tenant-1")

    assert alert is not None
    assert len(alert.alert_key) <= MAX_ALERT_KEY_LENGTH
    # 优先提取 jar 名，保证稳定且可读
    assert alert.alert_key == "lcmdb-172.16.11.196-进程-foundation-api.jar"
    assert alert.severity == "medium"  # "错误" 不在 SEVERITY_MAP，走默认 medium
    assert alert.metric_name == "运行数"
    assert alert.metric_value == "0"
    assert alert.instance_name == "主数据管理平台-生产环境-App服务器1"


@pytest.mark.asyncio
async def test_parse_invalid_payload_returns_none():
    adapter = LcmdbAdapter()
    assert await adapter.parse({"msgtype": "text"}, "tenant-1") is None
    assert await adapter.parse({"markdown": {}}, "tenant-1") is None


@pytest.mark.asyncio
async def test_parse_disk_alert_keeps_short_name():
    adapter = LcmdbAdapter()
    text = (
        "告警对象：企业知识库-测试环境 的 [磁盘:Disk]\n"
        "当前状态：警告\n"
        "IP地址：10.0.0.8\n"
        "当前:使用率=[92];\n"
    )
    alert = await adapter.parse(_raw_alert(text), "tenant-1")

    assert alert is not None
    assert alert.alert_key == "lcmdb-10.0.0.8-Disk"
    assert alert.instance_name == "企业知识库-测试环境"


def test_extract_short_name_no_bracket_truncates_title():
    name = _extract_short_name("这是一条没有方括号的超长告警对象标题" * 5)
    assert len(name) == 20


def test_extract_short_name_long_value_uses_hash_suffix():
    long_value = "x" * 200
    name = _extract_short_name(f"主机 的 [自定义:{long_value}]")
    assert len(name) <= 80 + 9
    assert name.endswith("-" + __import__("hashlib").sha256(long_value.encode()).hexdigest()[:8])


def test_clamp_alert_key_short_unchanged():
    key = "lcmdb-1.1.1.1-Disk"
    assert _clamp_alert_key(key) == key


def test_clamp_alert_key_long_truncated_with_hash():
    key = "lcmdb-1.1.1.1-" + ("a" * 300)
    clamped = _clamp_alert_key(key)
    assert len(clamped) == MAX_ALERT_KEY_LENGTH
    assert clamped.startswith("lcmdb-1.1.1.1-")
