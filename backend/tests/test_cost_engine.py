"""Unit tests for five-dimension cost breakdown."""

from decimal import Decimal

import pytest

from app.services.cost_engine import calculate_5d_cost


def _sku(
    category: str,
    model: str,
    cost_dimension: str,
    base_price: float,
    channel_price: float | None = None,
) -> dict:
    return {
        "category": category,
        "model": model,
        "cost_dimension": cost_dimension,
        "base_price": base_price,
        "channel_price": channel_price,
    }


class TestCalculate5dCost:
    def test_basic_dimension_aggregation(self) -> None:
        bom = [
            {"sku": _sku("GPU", "H800", "COMPUTE", 250000, 240000), "quantity": 512},
            {"sku": _sku("SWITCH", "QM9700", "NETWORK", 180000), "quantity": 24},
            {"sku": _sku("STORAGE", "NVMe_Array", "STORAGE", 50000), "quantity": 8},
        ]

        result = calculate_5d_cost(bom, pricing_rules={})

        assert result["COMPUTE"] == pytest.approx(512 * 240000)
        assert result["NETWORK"] == pytest.approx(24 * 180000)
        assert result["STORAGE"] == pytest.approx(8 * 50000)
        assert result["SOFTWARE"] == pytest.approx(0)
        hardware_subtotal = result["COMPUTE"] + result["NETWORK"] + result["STORAGE"]
        assert result["INFRA"] == pytest.approx(hardware_subtotal * 0.05)

    def test_channel_price_fallback_to_base(self) -> None:
        bom = [
            {"sku": _sku("GPU", "H800", "COMPUTE", 250000, None), "quantity": 10},
        ]
        result = calculate_5d_cost(bom)
        assert result["COMPUTE"] == pytest.approx(2500000)

    def test_free_scheduler_pricing_rule(self) -> None:
        bom = [
            {"sku": _sku("GPU", "H800", "COMPUTE", 100000), "quantity": 64},
            {
                "sku": _sku("SOFTWARE", "Basic_Scheduler", "SOFTWARE", 50000),
                "quantity": 1,
            },
        ]

        without_rule = calculate_5d_cost(bom, pricing_rules={})
        with_rule = calculate_5d_cost(
            bom, pricing_rules={"free_scheduler_with_server": True}
        )

        assert without_rule["SOFTWARE"] == pytest.approx(50000)
        assert with_rule["SOFTWARE"] == pytest.approx(0)
        assert with_rule["INFRA"] < without_rule["INFRA"]

    def test_512_gpu_cluster_cost_snapshot(self) -> None:
        """End-to-end cost breakdown for a 512-GPU BOM aligned with topology output."""
        bom = [
            {"sku": _sku("GPU", "H800 80G", "COMPUTE", 280000, 265000), "quantity": 512},
            {"sku": _sku("SWITCH", "Leaf-64", "NETWORK", 120000), "quantity": 16},
            {"sku": _sku("SWITCH", "Spine-64", "NETWORK", 150000), "quantity": 8},
            {"sku": _sku("OPTIC", "400G-SR8", "NETWORK", 800), "quantity": 1024},
            {"sku": _sku("STORAGE", "Ceph_Node", "STORAGE", 80000), "quantity": 12},
            {
                "sku": _sku("SOFTWARE", "Basic_Scheduler", "SOFTWARE", 120000),
                "quantity": 1,
            },
        ]

        result = calculate_5d_cost(
            bom, pricing_rules={"free_scheduler_with_server": True}
        )

        compute = 512 * 265000
        network = 16 * 120000 + 8 * 150000 + 1024 * 800
        storage = 12 * 80000
        software = 0.0
        hardware = compute + network + storage + software
        infra = hardware * 0.05

        assert result["COMPUTE"] == pytest.approx(compute)
        assert result["NETWORK"] == pytest.approx(network)
        assert result["STORAGE"] == pytest.approx(storage)
        assert result["SOFTWARE"] == pytest.approx(software)
        assert result["INFRA"] == pytest.approx(infra)
        assert sum(result.values()) == pytest.approx(hardware + infra)

    def test_unknown_cost_dimension_raises(self) -> None:
        bom = [
            {
                "sku": {
                    "category": "GPU",
                    "model": "X",
                    "cost_dimension": "UNKNOWN",
                    "base_price": 100,
                },
                "quantity": 1,
            }
        ]
        with pytest.raises(ValueError, match="Unknown cost dimension"):
            calculate_5d_cost(bom)

    def test_custom_infra_overhead_ratio(self) -> None:
        bom = [{"sku": _sku("GPU", "H800", "COMPUTE", 100000), "quantity": 10}]
        result = calculate_5d_cost(bom, infra_overhead_ratio=Decimal("0.10"))
        assert result["INFRA"] == pytest.approx(1000000 * 0.10)
