import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_consultation_hospital_10p(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/consultation/chat",
        json={"message": "想为一个医院提供10P的算力，做影像AI辅助诊断"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"]
    assert "医疗" in data["reply"] or "10" in data["reply"]
    assert len(data["messages"]) >= 2


@pytest.mark.asyncio
async def test_consultation_follow_up_ready(client: AsyncClient, auth_headers: dict):
    project_id = str(uuid4())
    r1 = await client.post(
        "/api/v1/consultation/chat",
        json={"message": "医院需要10P算力", "project_id": project_id},
        headers=auth_headers,
    )
    session_id = r1.json()["session_id"]

    r2 = await client.post(
        "/api/v1/consultation/chat",
        json={
            "session_id": session_id,
            "project_id": project_id,
            "message": "推理场景，每节点8卡，等保三级，主要用于CT影像分析",
        },
        headers=auth_headers,
    )
    data = r2.json()
    assert data["ready_to_generate"] is True
    assert data["extracted"]["target_gpus"] is not None
    assert data["extracted"]["scenario"] == "INFERENCE"


@pytest.mark.asyncio
async def test_consultation_project_isolation(client: AsyncClient, auth_headers: dict):
    session_id = str(uuid4())
    project_a = str(uuid4())
    project_b = str(uuid4())

    await client.post(
        "/api/v1/consultation/chat",
        json={
            "session_id": session_id,
            "project_id": project_a,
            "message": "医院需要10P算力，推理场景，8卡节点，等保三级",
        },
        headers=auth_headers,
    )

    r_b = await client.post(
        "/api/v1/consultation/chat",
        json={
            "session_id": session_id,
            "project_id": project_b,
            "message": "你好",
        },
        headers=auth_headers,
    )
    assert r_b.status_code == 200
    data = r_b.json()
    assert data["ready_to_generate"] is False
    assert "10" not in data.get("reply", "") or "算力" in data.get("reply", "")


@pytest.mark.asyncio
async def test_apply_consultation_plan_creates_project(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/consultation/apply-plan",
        json={
            "extracted": {
                "target_gpus": 64,
                "scenario": "MIXED",
                "gpus_per_node": 8,
                "switch_ports": 32,
                "project_name": "64卡混合集群",
                "scheme_summary": "8节点64卡Fat-Tree集群",
            },
            "requirement_text": "64 GPU mixed training inference cluster",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"]
    assert data["project_name"] == "64卡混合集群"
    assert data["bom_count"] > 0
    assert data["topology_result"]["compute"]["gpus"] == 64


@pytest.mark.asyncio
async def test_consultation_stream_rule(client: AsyncClient, auth_headers: dict):
    async with client.stream(
        "POST",
        "/api/v1/consultation/chat/stream",
        json={"message": "医院10P算力", "project_id": str(uuid4())},
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        body = ""
        async for chunk in response.aiter_text():
            body += chunk

    assert "event: token" in body
    assert "event: done" in body
