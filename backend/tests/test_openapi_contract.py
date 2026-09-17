"""OpenAPI / 路由契约冒烟测试（不依赖真实 DB）"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_openapi_includes_overview(client):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/alerts/overview" in schema["paths"]


def test_openapi_api_key_create_accepts_body(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/auth/api-keys"]["post"]
    body = path.get("requestBody")
    assert body is not None, "create api key must accept JSON body"
    content = body["content"]["application/json"]["schema"]
    # $ref 到 APIKeyCreateRequest
    assert "APIKeyCreateRequest" in str(content)


def test_openapi_register_has_response_model(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/auth/register"]["post"]
    resp = path["responses"]["200"]
    assert "RegisterResponse" in str(resp)


def test_openapi_me_has_response_model(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/auth/me"]["get"]
    assert "CurrentUserResponse" in str(path["responses"]["200"])


def test_openapi_dispose_message_response(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/alerts/{alert_id}/dispose"]["post"]
    assert "MessageResponse" in str(path["responses"]["200"])


def test_health_or_docs_available(client):
    # 应用可加载即可；避免强依赖健康检查路径
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "openapi" in schema.json()


def test_core_schemas_enums():
    from apps.core.schemas import AlertSeverity, AlertStatus
    assert AlertStatus.FIRING.value == "firing"
    assert AlertSeverity.CRITICAL.value == "critical"


def test_get_db_commits_only_open_transaction():
    import inspect
    from apps.core import database
    src = inspect.getsource(database.get_db)
    assert "in_transaction" in src
