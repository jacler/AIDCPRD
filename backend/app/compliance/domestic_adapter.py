"""Domestic (信创) substitution with ecosystem compatibility checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FRAMEWORK_MATRIX_PATH = (
    _REPO_ROOT / "data" / "public_sources" / "compatibility" / "framework_matrix.json"
)
_REPLACEMENTS_PATH = (
    _REPO_ROOT / "data" / "public_sources" / "compatibility" / "domestic_replacements.json"
)


@dataclass
class ReplacementItem:
    original_vendor: str
    original_model: str
    domestic_vendor: str
    domestic_model: str
    public_source: str


@dataclass
class CompatibilityGap:
    framework: str
    target_stack: str
    status: str
    compatibility_gap: str
    remediation: str


@dataclass
class DomesticAdaptationResult:
    enabled: bool
    replacements: list[ReplacementItem] = field(default_factory=list)
    unmatched: list[dict[str, str]] = field(default_factory=list)
    compatibility_gaps: list[CompatibilityGap] = field(default_factory=list)
    frameworks_requested: list[str] = field(default_factory=list)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_replacement_map() -> dict[tuple[str, str], ReplacementItem]:
    data = _load_json(_REPLACEMENTS_PATH)
    mapping: dict[tuple[str, str], ReplacementItem] = {}
    for row in data.get("replacements", []):
        key = (row["original_vendor"].lower(), row["original_model"].lower())
        mapping[key] = ReplacementItem(**row)
    return mapping


def check_framework_compatibility(
    framework: str,
    target_vendor: str,
) -> CompatibilityGap | None:
    """Check framework vs accelerator vendor using public compatibility matrix."""
    matrix = _load_json(_FRAMEWORK_MATRIX_PATH)
    fw_key = framework.strip().lower()
    vendor_key = target_vendor.strip().lower()
    if vendor_key in ("huawei", "ascend"):
        vendor_key = "ascend"

    fw_data = matrix.get("frameworks", {}).get(fw_key)
    if not fw_data:
        return CompatibilityGap(
            framework=framework,
            target_stack=target_vendor,
            status="unknown",
            compatibility_gap=f"框架 {framework} 未在公开兼容矩阵中定义",
            remediation="补充公开来源后重新评估，或选择矩阵内已验证框架",
        )

    vendor_entry = fw_data.get(vendor_key)
    if not vendor_entry:
        return CompatibilityGap(
            framework=framework,
            target_stack=target_vendor,
            status="unsupported",
            compatibility_gap=f"{framework} 未声明对 {target_vendor} 的官方支持",
            remediation="更换框架或选择矩阵内 native/partial 支持的硬件栈",
        )

    status = vendor_entry.get("status", "unknown")
    if status in ("native", "supported"):
        return None

    return CompatibilityGap(
        framework=framework,
        target_stack=vendor_entry.get("stack", target_vendor),
        status=status,
        compatibility_gap=vendor_entry.get(
            "compatibility_gap", f"{framework} 在 {target_vendor} 上为 {status} 状态"
        ),
        remediation=vendor_entry.get(
            "remediation", "请查阅厂商公开迁移指南并完成 POC 验证"
        ),
    )


def adapt_catalog_items(
    bom_items: list[dict[str, str]],
    *,
    domestic_mode: bool,
    frameworks: list[str] | None = None,
) -> DomesticAdaptationResult:
    """Replace SKU entries with domestic alternatives when domestic_mode is on."""
    frameworks = frameworks or []
    if not domestic_mode:
        return DomesticAdaptationResult(enabled=False, frameworks_requested=frameworks)

    replacement_map = _load_replacement_map()
    replacements: list[ReplacementItem] = []
    unmatched: list[dict[str, str]] = []
    gaps: list[CompatibilityGap] = []

    for item in bom_items:
        vendor = str(item.get("vendor", ""))
        model = str(item.get("model", ""))
        key = (vendor.lower(), model.lower())
        repl = replacement_map.get(key)
        if repl:
            replacements.append(repl)
        else:
            unmatched.append({"vendor": vendor, "model": model, "category": item.get("category", "")})

    target_vendor = "Ascend" if domestic_mode else "NVIDIA"
    for fw in frameworks:
        gap = check_framework_compatibility(fw, target_vendor)
        if gap:
            gaps.append(gap)

    return DomesticAdaptationResult(
        enabled=True,
        replacements=replacements,
        unmatched=unmatched,
        compatibility_gaps=gaps,
        frameworks_requested=frameworks,
    )
