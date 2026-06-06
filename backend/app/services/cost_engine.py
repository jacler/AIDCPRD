"""Five-dimension cost breakdown engine."""

from decimal import Decimal
from typing import Any

COST_DIMENSIONS = ("COMPUTE", "NETWORK", "STORAGE", "SOFTWARE", "INFRA")

INFRA_OVERHEAD_RATIO = Decimal("0.05")


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _resolve_unit_price(sku: dict[str, Any]) -> Decimal:
    channel_price = sku.get("channel_price")
    if channel_price is not None:
        return _to_decimal(channel_price)
    return _to_decimal(sku["base_price"])


def _apply_pricing_rules(
    sku: dict[str, Any], subtotal: Decimal, pricing_rules: dict[str, Any]
) -> Decimal:
    if (
        pricing_rules.get("free_scheduler_with_server")
        and sku.get("category") == "SOFTWARE"
        and sku.get("model") == "Basic_Scheduler"
    ):
        return Decimal("0")
    return subtotal


def calculate_5d_cost(
    bom_items: list[dict[str, Any]],
    pricing_rules: dict[str, Any] | None = None,
    infra_overhead_ratio: Decimal | float = INFRA_OVERHEAD_RATIO,
) -> dict[str, float]:
    """
    Map BOM line items to five cost dimensions and apply business pricing rules.

    After hardware/software subtotals are aggregated, implicit infra cost
    (implementation & maintenance) is estimated as a ratio of total hardware spend.
    """
    rules = pricing_rules or {}
    ratio = _to_decimal(infra_overhead_ratio)

    cost_breakdown: dict[str, Decimal] = {dim: Decimal("0") for dim in COST_DIMENSIONS}

    for item in bom_items:
        sku = item["sku"]
        qty = int(item["quantity"])
        unit_price = _resolve_unit_price(sku)
        subtotal = _to_decimal(qty) * unit_price
        subtotal = _apply_pricing_rules(sku, subtotal, rules)

        dimension = sku["cost_dimension"]
        if dimension not in cost_breakdown:
            raise ValueError(f"Unknown cost dimension: {dimension}")

        cost_breakdown[dimension] += subtotal

    total_hardware = sum(cost_breakdown.values())
    cost_breakdown["INFRA"] += total_hardware * ratio

    return {dim: float(cost_breakdown[dim]) for dim in COST_DIMENSIONS}
