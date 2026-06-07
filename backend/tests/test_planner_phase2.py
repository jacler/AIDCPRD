"""Phase 2 acceptance — multi-plan trade-off matrix & TCO."""

import pytest
from httpx import AsyncClient

from app.planner.multi_plan import build_multi_plans
from app.rules.tco_calculator import TCOInput, calculate_5y_tco, electricity_sensitivity


def test_tco_electricity_formula():
    params = TCOInput(
        hardware_capex_cny=10_000_000,
        target_gpus=64,
        servers=8,
        leaf_switches=4,
        spine_switches=2,
        storage_nodes=4,
        electricity_price_cny_per_kwh=1.0,
        pue=1.5,
    )
    result = calculate_5y_tco(params)
    power_kw = result.breakdown.total_power_kw
    expected_annual = power_kw * 1.5 * 1.0 * 8760
    assert abs(result.breakdown.electricity_annual - expected_annual) < 1.0
    assert result.breakdown.total_5y > params.hardware_capex_cny


def test_electricity_price_changes_tco():
    base = TCOInput(
        hardware_capex_cny=5_000_000,
        target_gpus=128,
        servers=16,
        leaf_switches=8,
        spine_switches=4,
        storage_nodes=6,
        electricity_price_cny_per_kwh=0.6,
    )
    high = TCOInput(**{**base.__dict__, "electricity_price_cny_per_kwh": 1.2})
    assert calculate_5y_tco(high).breakdown.total_5y > calculate_5y_tco(base).breakdown.total_5y


def test_build_three_plans_with_tradeoff_fields():
    plans = build_multi_plans(
        cost_breakdown={
            "COMPUTE": 20_000_000,
            "NETWORK": 2_000_000,
            "STORAGE": 1_000_000,
            "SOFTWARE": 500_000,
            "INFRA": 1_000_000,
            "total": 24_500_000,
        },
        target_gpus=256,
        topology={
            "compute": {"servers": 32, "gpus": 256},
            "network": {"leaf_switches": 8, "spine_switches": 4},
            "storage": {"nodes": 8},
        },
        scenario="TRAINING",
        electricity_price_cny_per_kwh=0.8,
    )
    assert len(plans) == 3
    ids = {p["plan_id"] for p in plans}
    assert ids == {"performance_optimized", "balanced", "cost_optimized"}
    for plan in plans:
        assert plan["headline"]
        assert len(plan["trade_offs"]) >= 1
        assert plan["failure_boundary"]
        assert plan["tco_sensitivity"]["variable"] == "electricity_price"
        assert "impact_pct" in plan["tco_sensitivity"]
        assert plan["tco_5y"] > 0

    cost_plan = next(p for p in plans if p["plan_id"] == "cost_optimized")
    perf_plan = next(p for p in plans if p["plan_id"] == "performance_optimized")
    assert cost_plan["hardware_capex"] < perf_plan["hardware_capex"]


@pytest.mark.asyncio
async def test_multi_plan_api(client: AsyncClient, auth_headers: dict, seed_skus):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "TCO测试", "target_gpus": 64, "scenario": "MIXED"},
        headers=auth_headers,
    )
    project_id = create.json()["id"]

    await client.post(
        "/api/v1/projects/generate-topology",
        json={
            "target_gpus": 64,
            "scenario": "MIXED",
            "project_id": project_id,
        },
        headers=auth_headers,
    )

    r1 = await client.get(
        f"/api/v1/projects/{project_id}/multi-plan?electricity_price=0.6",
        headers=auth_headers,
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert len(data1["plans"]) == 3

    r2 = await client.get(
        f"/api/v1/projects/{project_id}/multi-plan?electricity_price=1.2",
        headers=auth_headers,
    )
    data2 = r2.json()
    tco_low = sum(p["tco_5y"] for p in data1["plans"])
    tco_high = sum(p["tco_5y"] for p in data2["plans"])
    assert tco_high > tco_low
