import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_consultation_prompt_presets(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        "/api/v1/settings/consultation/prompt-presets",
        headers=auth_headers,
    )
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) == 5
    assert presets[0]["id"] == "general"
    assert presets[0]["editable"] is False
    assert len(presets[0]["guided_steps"]) >= 4
    assert "prompt" not in presets[0]


@pytest.mark.asyncio
async def test_update_consultation_preset(client: AsyncClient, auth_headers: dict):
    response = await client.put(
        "/api/v1/settings/consultation",
        json={"system_prompt_preset_id": "healthcare"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["system_prompt_preset_id"] == "healthcare"
    assert "医疗" in data["system_prompt"]


@pytest.mark.asyncio
async def test_get_consultation_settings(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/settings/consultation", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["chat_endpoint"] == "/api/v1/consultation/chat"
    assert data["provider"] in ("rule", "openai_compatible")


@pytest.mark.asyncio
async def test_update_consultation_settings_admin(client: AsyncClient, auth_headers: dict):
    response = await client.put(
        "/api/v1/settings/consultation",
        json={
            "provider": "rule",
            "enabled": True,
            "model": "gpt-4o-mini",
            "system_prompt": "测试提示词",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["system_prompt"] == "测试提示词"


@pytest.mark.asyncio
async def test_consultation_test_rule_mode(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/settings/consultation/test",
        json={"message": "医院10P算力"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_format_llm_api_error_401_openai():
    from app.services.consultation_config import format_llm_api_error

    msg = format_llm_api_error(
        401,
        '{"error":{"message":"Incorrect API key provided"}}',
        "https://api.openai.com/v1",
    )
    assert "401" in msg
    assert "OpenAI" in msg


def test_normalize_api_key_strips_wrappers():
    from app.services.consultation_config import normalize_api_key

    assert normalize_api_key("Bearer sk-abc123xyz") == "sk-abc123xyz"
    assert normalize_api_key("密钥：sk-abc123xyz") == "sk-abc123xyz"
    assert normalize_api_key("  sk-test_key-99  ") == "sk-test_key-99"


def test_extract_partial_reply():
    from app.services.consultation_config import ReplyFieldExtractor, extract_partial_reply

    partial = '{"reply":"你好，这是'
    assert extract_partial_reply(partial) == "你好，这是"

    extractor = ReplyFieldExtractor()
    assert extractor.feed('{"reply":"医疗') == "医疗"
    assert extractor.feed('场景分析\\n继续"') == "场景分析\n继续"
