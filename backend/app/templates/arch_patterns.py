"""AIDC V3.0 architecture pattern templates — deterministic selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_PATTERN_ALIASES = {
    "fat_tree": "fat_tree_inference",
    "hybrid": "hybrid_campus",
}


@dataclass(frozen=True)
class ArchPattern:
    pattern_id: str
    display_name: str
    use_case: str
    key_visual_rules: dict[str, Any]
    layout_hints: dict[str, Any]
    compliance_notes: str
    match_keywords: tuple[str, ...]
    default_convergence: str
    network_tiers: tuple[str, ...]


ARCH_PATTERNS: tuple[ArchPattern, ...] = (
    ArchPattern(
        pattern_id="rail_optimized",
        display_name="Rail-Optimized 万卡训练架构",
        use_case="千亿参数大模型预训练",
        key_visual_rules={
            "gpu_grouping": "每8台服务器为一个Rail组，虚线框包裹",
            "network_tiers": ["Access", "Leaf", "Spine", "Core"],
            "storage_plane": "独立存储网络",
            "label_requirements": ["收敛比", "光模块类型", "链路带宽"],
        },
        layout_hints={
            "gpu_group_wrap": True,
            "storage_plane_separate": True,
            "spine_no_direct_server": True,
            "convergence_ratio_label": "1:1",
        },
        compliance_notes="需标注液冷/风冷区域分界",
        match_keywords=("万卡", "预训练", "千亿", "2048", "4096", "rail"),
        default_convergence="1:1",
        network_tiers=("Core", "Spine", "Leaf", "Compute", "Storage"),
    ),
    ArchPattern(
        pattern_id="fat_tree_inference",
        display_name="Fat-Tree 企业推理架构",
        use_case="企业级 SFT / 推理服务",
        key_visual_rules={
            "gpu_grouping": "计算节点均匀分布于 Leaf 下行",
            "network_tiers": ["Leaf", "Spine"],
            "storage_plane": "三网分离标注",
            "label_requirements": ["收敛比", "光模块", "带宽"],
        },
        layout_hints={
            "gpu_group_wrap": False,
            "storage_plane_separate": False,
            "spine_no_direct_server": True,
            "convergence_ratio_label": "3:1",
            "three_plane_separate": True,
        },
        compliance_notes="收敛比须在图中显式标注",
        match_keywords=("推理", "sft", "微调", "企业", "inference", "胖树"),
        default_convergence="3:1",
        network_tiers=("Spine", "Leaf", "Compute", "Storage", "Mgmt"),
    ),
    ArchPattern(
        pattern_id="hybrid_campus",
        display_name="Hybrid 训推一体园区架构",
        use_case="训推一体园区 / 多业务混合",
        key_visual_rules={
            "gpu_grouping": "训练/推理物理分区",
            "network_tiers": ["Core", "Spine", "Leaf", "Access"],
            "storage_plane": "管理/业务/存储三网分离",
            "label_requirements": ["收敛比", "Core 互通", "边界防护"],
        },
        layout_hints={
            "gpu_group_wrap": False,
            "storage_plane_separate": True,
            "spine_no_direct_server": True,
            "convergence_ratio_label": "2:1",
            "train_infer_isolated": True,
        },
        compliance_notes="跨域互通须标注边界防护",
        match_keywords=("训推", "混合", "园区", "hybrid", "mixed"),
        default_convergence="2:1",
        network_tiers=("Core", "Spine", "Leaf", "Compute", "Storage", "Mgmt"),
    ),
)

_PATTERNS_BY_ID: dict[str, ArchPattern] = {}
for p in ARCH_PATTERNS:
    _PATTERNS_BY_ID[p.pattern_id] = p
    if p.pattern_id == "fat_tree_inference":
        _PATTERNS_BY_ID["fat_tree"] = p
    if p.pattern_id == "hybrid_campus":
        _PATTERNS_BY_ID["hybrid"] = p


def get_pattern(pattern_id: str | None) -> ArchPattern | None:
    if not pattern_id:
        return None
    normalized = _PATTERN_ALIASES.get(pattern_id, pattern_id)
    return _PATTERNS_BY_ID.get(normalized)


def list_patterns() -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for p in ARCH_PATTERNS:
        if p.pattern_id in seen:
            continue
        seen.add(p.pattern_id)
        out.append(
            {
                "pattern_id": p.pattern_id,
                "display_name": p.display_name,
                "use_case": p.use_case,
                "key_visual_rules": p.key_visual_rules,
                "layout_hints": p.layout_hints,
                "compliance_notes": p.compliance_notes,
            }
        )
    return out


def auto_select_template(requirements: dict[str, Any]) -> str:
    """Select best template from structured requirements."""
    text = str(requirements.get("requirement", "") or "").lower()
    target_gpus = int(requirements.get("target_gpus") or 0)
    scenario = str(requirements.get("scenario", "") or "").upper()
    network = str(requirements.get("network_type", "") or "").lower()

    if target_gpus >= 512 or "2048" in text or any(k in text for k in ("万卡", "预训练", "千亿")):
        return "rail_optimized"

    if any(k in text for k in ("训推", "园区", "混合", "hybrid")):
        return "hybrid_campus"

    if scenario == "INFERENCE" or any(k in text for k in ("推理", "sft", "企业")):
        return "fat_tree_inference"

    if target_gpus <= 16:
        return "fat_tree_inference"

    if "roce" in network or "inference" in network:
        return "fat_tree_inference"

    return "hybrid_campus"


def match_pattern(requirement: str, *, target_gpus: int = 0, scenario: str = "") -> ArchPattern:
    pid = auto_select_template(
        {"requirement": requirement, "target_gpus": target_gpus, "scenario": scenario}
    )
    return _PATTERNS_BY_ID[pid]
