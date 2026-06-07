"""Five-year TCO calculator — deterministic, no LLM."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

HOURS_PER_YEAR = 8760
DEFAULT_YEARS = 5

# Reference TDP (W) from data/public_sources — not vendor-internal pricing
_GPU_TDP_W: dict[str, float] = {
    "default_training": 700.0,
    "default_inference": 350.0,
    "H800": 350.0,
    "H100": 700.0,
    "A100": 400.0,
    "L40S": 350.0,
    "MI300X": 750.0,
}
_SERVER_OVERHEAD_W = 500.0
_SWITCH_TDP_W = 350.0  # TODO: 需补充公开来源 — per 64-port datacenter switch class
_STORAGE_NODE_TDP_W = 800.0


@dataclass
class TCOInput:
    hardware_capex_cny: float
    target_gpus: int
    servers: int
    leaf_switches: int
    spine_switches: int
    storage_nodes: int
    scenario: str = "MIXED"
    electricity_price_cny_per_kwh: float = 0.8
    pue: float = 1.3
    maintenance_ratio_annual: float = 0.08
    implementation_ratio: float = 0.05
    years: int = DEFAULT_YEARS
    gpu_model_hint: str | None = None


@dataclass
class TCOBreakdown:
    hardware_capex: float
    implementation: float
    electricity_annual: float
    maintenance_annual: float
    total_5y: float
    total_power_kw: float


@dataclass
class TCOResult:
    breakdown: TCOBreakdown
    yearly_opex: float
    sensitivity: dict[str, Any] = field(default_factory=dict)


def _gpu_tdp_w(scenario: str, hint: str | None) -> float:
    if hint:
        for key, tdp in _GPU_TDP_W.items():
            if key in hint.upper():
                return tdp
    if scenario == "INFERENCE":
        return _GPU_TDP_W["default_inference"]
    return _GPU_TDP_W["default_training"]


def estimate_total_power_kw(params: TCOInput) -> float:
    """Estimate IT load (kW) from topology scale and public TDP references."""
    tdp = _gpu_tdp_w(params.scenario, params.gpu_model_hint)
    gpu_w = params.target_gpus * tdp
    server_w = params.servers * _SERVER_OVERHEAD_W
    switch_w = (params.leaf_switches + params.spine_switches) * _SWITCH_TDP_W
    storage_w = params.storage_nodes * _STORAGE_NODE_TDP_W
    total_w = gpu_w + server_w + switch_w + storage_w
    return round(total_w / 1000.0, 2)


def calculate_5y_tco(params: TCOInput) -> TCOResult:
    capex = Decimal(str(params.hardware_capex_cny))
    impl = capex * Decimal(str(params.implementation_ratio))
    power_kw = Decimal(str(estimate_total_power_kw(params)))
    elec_annual = (
        power_kw
        * Decimal(str(params.pue))
        * Decimal(str(params.electricity_price_cny_per_kwh))
        * Decimal(str(HOURS_PER_YEAR))
    )
    maint_annual = capex * Decimal(str(params.maintenance_ratio_annual))
    years = params.years
    total_5y = capex + impl + (elec_annual + maint_annual) * Decimal(str(years))

    breakdown = TCOBreakdown(
        hardware_capex=float(capex),
        implementation=float(impl),
        electricity_annual=float(elec_annual),
        maintenance_annual=float(maint_annual),
        total_5y=float(total_5y),
        total_power_kw=float(power_kw),
    )
    return TCOResult(
        breakdown=breakdown,
        yearly_opex=float(elec_annual + maint_annual),
    )


def electricity_sensitivity(
    params: TCOInput,
    *,
    delta_pct: float = 0.25,
) -> dict[str, Any]:
    """How much 5Y TCO moves when electricity price changes by ±delta_pct."""
    baseline = calculate_5y_tco(params)
    base_price = params.electricity_price_cny_per_kwh
    high = TCOInput(**{**params.__dict__, "electricity_price_cny_per_kwh": base_price * (1 + delta_pct)})
    low = TCOInput(**{**params.__dict__, "electricity_price_cny_per_kwh": base_price * (1 - delta_pct)})

    high_tco = calculate_5y_tco(high).breakdown.total_5y
    low_tco = calculate_5y_tco(low).breakdown.total_5y
    base_tco = baseline.breakdown.total_5y

    elec_share = (
        float(baseline.breakdown.electricity_annual) * params.years / base_tco * 100
        if base_tco
        else 0.0
    )

    return {
        "variable": "electricity_price",
        "impact_pct": round(elec_share, 1),
        "baseline_price_cny_per_kwh": base_price,
        "tco_at_minus_25pct": round(low_tco, 2),
        "tco_at_plus_25pct": round(high_tco, 2),
    }
