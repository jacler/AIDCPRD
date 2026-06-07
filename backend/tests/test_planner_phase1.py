"""Phase 1 acceptance tests — consultation planner."""

import pytest
from httpx import AsyncClient

from app.planner.diagnostic_tree import next_diagnostic_nodes
from app.planner.engine import ConsultationPlanner
from app.planner.intent_classifier import Intent, classify_intent


def test_classify_pretrain_fuzzy_low_confidence():
    result = classify_intent("想训个大模型")
    assert result.intent == Intent.PRETRAIN
    assert result.confidence < 0.8
    assert result.needs_clarification is True
    assert len(result.clarification_hints) >= 1


def test_classify_inference_high_confidence():
    result = classify_intent("在线推理服务，峰值 2000 QPS，P99 延迟 150ms")
    assert result.intent == Intent.INFERENCE
    assert result.confidence >= 0.8
    assert result.needs_clarification is False


def test_diagnostic_tree_pretrain_has_engineering_constraints():
    nodes = next_diagnostic_nodes(Intent.PRETRAIN, {}, set(), limit=2)
    assert len(nodes) >= 2
    assert all(n.engineering_constraint for n in nodes)
    assert all(n.engineering_purpose for n in nodes)
    constraints = {n.engineering_constraint for n in nodes}
    assert "affects_nvlink_topology" in constraints or "affects_storage_checkpoint" in constraints


def test_fuzzy_pretrain_two_round_follow_up():
    planner = ConsultationPlanner()
    slots: dict = {}
    asked: set[str] = set()

    turn1 = planner.plan_turn("想训个大模型", slots, asked)
    assert turn1.classification.needs_clarification
    assert len(turn1.diagnostic_questions) >= 2
    assert all(q.engineering_purpose for q in turn1.diagnostic_questions)
    assert "工程目的" in turn1.reply or "📐" in turn1.reply
    asked.update(turn1.asked_keys)

    turn2 = planner.plan_turn(
        "数据并行，每月约 10T Token，目标 512 张 GPU",
        {**slots, "parallel_strategy": "data_parallel", "token_scale_monthly": "10T", "target_gpus": 512},
        asked,
    )
    assert len(turn2.diagnostic_questions) >= 0
    assert turn2.reply


@pytest.mark.asyncio
async def test_api_fuzzy_pretrain_consultation(client: AsyncClient, auth_headers: dict):
    r1 = await client.post(
        "/api/v1/consultation/chat",
        json={"message": "想训个大模型"},
        headers=auth_headers,
    )
    assert r1.status_code == 200
    data = r1.json()
    assert data["intent"] == "pretrain"
    assert data["needs_clarification"] is True
    assert len(data["diagnostic_questions"]) >= 2
    assert all("engineering_purpose" in q for q in data["diagnostic_questions"])
    session_id = data["session_id"]

    r2 = await client.post(
        "/api/v1/consultation/chat",
        json={
            "session_id": session_id,
            "message": "数据并行，每月 10T Token，512 张 GPU，模型并行暂不需要",
        },
        headers=auth_headers,
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert len(data2["messages"]) >= 4
    assert any("工程目的" in m["content"] or "📐" in m["content"] for m in data2["messages"] if m["role"] == "assistant")
