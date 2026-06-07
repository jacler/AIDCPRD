"""Public hardware model catalog — compliance-safe device labels (V3.0)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODELS_PATH = _REPO_ROOT / "data" / "public_models.json"


@dataclass
class ModelInfo:
    model: str
    type: str
    label: str
    public: bool
    source: str
    key_param: str
    warnings: list[str] = field(default_factory=list)
    is_public_equivalent: bool = False

    # backward compat
    @property
    def is_public_equivalent_legacy(self) -> bool:
        return self.is_public_equivalent


# backward compat alias
ResolvedModel = ModelInfo


def load_public_models() -> list[dict[str, Any]]:
    if not _MODELS_PATH.is_file():
        return []
    return json.loads(_MODELS_PATH.read_text(encoding="utf-8"))


def _key_param(entry: dict[str, Any]) -> str:
    if entry.get("ports"):
        return str(entry["ports"])
    if entry.get("nic"):
        return str(entry["nic"])
    if entry.get("gpu_count"):
        return f"{entry['gpu_count']}x GPU"
    if entry.get("protocol"):
        return str(entry["protocol"])
    return "公开规格"


def _role_for_type(device_type: str) -> str:
    return {
        "gpu_server": "AI 训练服务器",
        "gpu": "AI 加速卡",
        "leaf_switch": "Leaf 接入交换机",
        "spine_switch": "Spine 汇聚交换机",
        "core_switch": "Core 核心交换机",
        "storage": "并行文件存储",
        "mgmt_switch": "带外管理交换机",
    }.get(device_type, "网络设备")


def _find_entry(name: str, catalog: list[dict[str, Any]]) -> dict[str, Any] | None:
    lower = name.lower().strip()
    for item in catalog:
        if item.get("model", "").lower() == lower:
            return item
    for item in catalog:
        m = item.get("model", "").lower()
        if lower in m or m in lower:
            return item
    return None


def resolve_model(user_input: str) -> ModelInfo:
    """Resolve device name — public catalog or internal→public equivalent."""
    catalog = load_public_models()
    warnings: list[str] = []
    entry = _find_entry(user_input, catalog)

    if entry and entry.get("internal_only"):
        equiv_name = entry.get("public_equivalent", "")
        equiv = _find_entry(equiv_name, catalog) if equiv_name else None
        warnings.append(f"已替换为公开等效型号: {equiv_name}")
        if equiv:
            entry = equiv
            is_equiv = True
        else:
            is_equiv = True
            return ModelInfo(
                model=equiv_name or user_input,
                type=str(entry.get("type", "device")),
                label=f"{equiv_name or user_input} (Public Equivalent)",
                public=True,
                source="data/public_models.json",
                key_param=_key_param(entry),
                warnings=warnings,
                is_public_equivalent=True,
            )
    elif entry and entry.get("public", True):
        is_equiv = False
    else:
        # closest match by type keyword
        closest = catalog[0] if catalog else None
        for item in catalog:
            if item.get("public", True) and user_input.lower() in item.get("type", ""):
                closest = item
                break
        if closest:
            warnings.append("未找到精确匹配，已使用近似公开型号")
            entry = closest
            is_equiv = True
        else:
            return ModelInfo(
                model=user_input,
                type="device",
                label=f"{user_input} (Public Equivalent)",
                public=False,
                source="data/public_models.json — TODO: 需补充公开来源",
                key_param="待补充",
                warnings=["未找到匹配型号，使用占位标注"],
                is_public_equivalent=True,
            )

    model_name = str(entry["model"])
    device_type = str(entry.get("type", "device"))
    param = _key_param(entry)
    from app.visualizer.aidc_golden_rules import device_label

    label = device_label(model_name, _role_for_type(device_type), param)
    if is_equiv:
        label = device_label(f"{model_name} (Public Equivalent)", _role_for_type(device_type), param)

    return ModelInfo(
        model=model_name,
        type=device_type,
        label=label,
        public=bool(entry.get("public", True)),
        source=str(entry.get("source") or "data/public_models.json"),
        key_param=param,
        warnings=warnings,
        is_public_equivalent=is_equiv,
    )


def default_models_for_pattern(pattern_id: str) -> dict[str, ModelInfo]:
    pid = pattern_id.replace("fat_tree", "fat_tree_inference").replace("hybrid", "hybrid_campus")
    gpu = resolve_model("8-GPU Training Server")
    leaf = resolve_model("NVIDIA Quantum-2 QM9700")
    spine = resolve_model("NVIDIA Spectrum-4 SN5600")
    core = resolve_model("Arista 7800R3")
    storage = resolve_model("Parallel File Storage Node")
    mgmt = resolve_model("Management Switch 25G")
    return {
        "gpu_server": gpu,
        "leaf": leaf,
        "spine": spine,
        "core": core,
        "storage": storage,
        "mgmt": mgmt,
    }
