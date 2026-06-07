"""Multi-plan trade-off matrix — deterministic plan variants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.rules.tco_calculator import TCOInput, calculate_5y_tco, electricity_sensitivity


@dataclass(frozen=True)
class PlanProfile:
    plan_id: str
    headline: str
    trade_offs: tuple[str, ...]
    failure_boundary: str
    network_cost_factor: float
    compute_cost_factor: float
    convergence_ratio: str
    network_technology: str
    mfu_relative: float


PLAN_PROFILES: tuple[PlanProfile, ...] = (
    PlanProfile(
        plan_id="performance_optimized",
        headline="性能优先，全 IB 无收敛 Fat-Tree，适合大规模预训练",
        trade_offs=(
            "网络设备 CAPEX 较均衡方案高约 15%",
            "单卡 TCO 偏高，IB 交换机与光模块溢价明显",
        ),
        failure_boundary="当集群规模 < 64 GPU 时，IB 投资回报率偏低",
        network_cost_factor=1.15,
        compute_cost_factor=1.0,
        convergence_ratio="1:1",
        network_technology="InfiniBand NDR",
        mfu_relative=1.0,
    ),
    PlanProfile(
        plan_id="balanced",
        headline="均衡方案，标准 Fat-Tree，训推混合场景通用",
        trade_offs=(
            "成本与性能折中，运维复杂度适中",
            "超千卡扩展时需评估 Spine 层预算",
        ),
        failure_boundary="当 AllReduce 通信占比 > 40% 时，建议升级至性能优先方案",
        network_cost_factor=1.0,
        compute_cost_factor=1.0,
        convergence_ratio="1:1",
        network_technology="IB / RoCE 混合可行",
        mfu_relative=0.92,
    ),
    PlanProfile(
        plan_id="cost_optimized",
        headline="极致性价比，适合预算敏感型 SFT / 推理任务",
        trade_offs=(
            "采用 3:1 收敛比，大规模 AllReduce 通信效率下降约 15%",
            "以太网 RoCE 生态，MFU 较 IB 方案低 10–15%",
        ),
        failure_boundary="当单卡显存占用 > 70GB 时，OOM 风险显著上升",
        network_cost_factor=0.82,
        compute_cost_factor=0.95,
        convergence_ratio="3:1",
        network_technology="RoCEv2 Ethernet",
        mfu_relative=0.85,
    ),
)


def _scale_breakdown(base: dict[str, float], profile: PlanProfile) -> dict[str, float]:
    scaled = dict(base)
    scaled["COMPUTE"] = base.get("COMPUTE", 0) * profile.compute_cost_factor
    scaled["NETWORK"] = base.get("NETWORK", 0) * profile.network_cost_factor
    scaled["STORAGE"] = base.get("STORAGE", 0)
    scaled["SOFTWARE"] = base.get("SOFTWARE", 0)
    scaled["INFRA"] = base.get("INFRA", 0)
    scaled["total"] = sum(scaled[k] for k in ("COMPUTE", "NETWORK", "STORAGE", "SOFTWARE", "INFRA"))
    return {k: round(v, 2) for k, v in scaled.items()}


def build_multi_plans(
    *,
    cost_breakdown: dict[str, float] | None,
    target_gpus: int,
    topology: dict[str, Any] | None,
    scenario: str,
    electricity_price_cny_per_kwh: float = 0.8,
    pue: float = 1.3,
) -> list[dict[str, Any]]:
    """Build three plan variants with TCO and trade-off matrix fields."""
    base = cost_breakdown or {
        "COMPUTE": target_gpus * 265_000,
        "NETWORK": max(8, target_gpus // 8) * 120_000,
        "STORAGE": max(3, target_gpus // 16) * 80_000,
        "SOFTWARE": 120_000,
        "INFRA": target_gpus * 15_000,
    }
    base["total"] = base.get("total") or sum(
        base.get(k, 0) for k in ("COMPUTE", "NETWORK", "STORAGE", "SOFTWARE", "INFRA")
    )

    compute = (topology or {}).get("compute") or {}
    network = (topology or {}).get("network") or {}
    storage = (topology or {}).get("storage") or {}

    servers = int(compute.get("servers") or max(1, target_gpus // 8))
    leaf = int(network.get("leaf_switches") or max(2, servers // 16))
    spine = int(network.get("spine_switches") or max(2, leaf // 2))
    storage_nodes = int(storage.get("nodes") or max(3, servers // 12))

    plans: list[dict[str, Any]] = []
    for profile in PLAN_PROFILES:
        scaled = _scale_breakdown(base, profile)
        tco_in = TCOInput(
            hardware_capex_cny=scaled["total"],
            target_gpus=target_gpus,
            servers=servers,
            leaf_switches=leaf,
            spine_switches=spine,
            storage_nodes=storage_nodes,
            scenario=scenario,
            electricity_price_cny_per_kwh=electricity_price_cny_per_kwh,
            pue=pue,
        )
        tco = calculate_5y_tco(tco_in)
        sensitivity = electricity_sensitivity(tco_in)

        plans.append(
            {
                "plan_id": profile.plan_id,
                "headline": profile.headline,
                "trade_offs": list(profile.trade_offs),
                "failure_boundary": profile.failure_boundary,
                "tco_sensitivity": sensitivity,
                "convergence_ratio": profile.convergence_ratio,
                "network_technology": profile.network_technology,
                "mfu_relative": profile.mfu_relative,
                "cost_breakdown": scaled,
                "hardware_capex": scaled["total"],
                "tco_5y": round(tco.breakdown.total_5y, 2),
                "tco_breakdown": {
                    "hardware_capex": tco.breakdown.hardware_capex,
                    "implementation": tco.breakdown.implementation,
                    "electricity_annual": tco.breakdown.electricity_annual,
                    "maintenance_annual": tco.breakdown.maintenance_annual,
                    "total_power_kw": tco.breakdown.total_power_kw,
                },
                "recommended": profile.plan_id == "balanced",
            }
        )

    return plans
