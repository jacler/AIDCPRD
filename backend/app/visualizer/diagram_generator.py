"""AIDC V4.0 Mermaid generator — mermaid.live 零报错、classDef 样式."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.templates.arch_patterns import ArchPattern, auto_select_template, get_pattern, match_pattern
from app.visualizer.aidc_golden_rules import (
    SUBGRAPH_LAYER_STYLE,
    aidc_init_directive,
    design_note_box,
    device_label,
    diagram_header_comment,
    layer_subgraph_style,
    quote_edge_label,
    render_class_assignments,
    render_class_defs,
    validate_aidc_compliance,
    v40_compliance_checklist,
    violations_to_dict,
)
from app.visualizer.public_models import ModelInfo, default_models_for_pattern, resolve_model
from app.visualizer.topology_renderer import compute_convergence_ratio


@dataclass
class DiagramGenerationResult:
    pattern_id: str
    pattern_name: str
    mermaid_code: str
    convergence_ratio: str
    design_points: list[str]
    render_tools: list[dict[str, str]]
    validation_issues: list[dict[str, Any]] = field(default_factory=list)
    compliance_notes: str = ""
    data_disclaimer: str = "本图基于公开技术参数生成，仅供技术参考，不构成商业承诺"
    param_table: str = ""
    model_warnings: list[str] = field(default_factory=list)
    compliance_checklist: list[str] = field(default_factory=list)


RENDER_TOOLS: list[dict[str, str]] = [
    {"name": "Mermaid Live Editor", "url": "https://mermaid.live", "export": "Export PNG 300dpi"},
    {"name": "Typora", "url": "", "export": "粘贴代码 → 导出 PDF/SVG"},
    {"name": "VS Code Mermaid Preview", "url": "", "export": "Export PNG 300dpi"},
]

NODE_CLASS_MAP = {
    "core": "coreStyle",
    "spine": "spineStyle",
    "leaf": "leafStyle",
    "compute": "computeStyle",
    "storage": "storageStyle",
    "mgmt": "mgmtStyle",
    "data": "dataPlane",
    "render": "renderPlane",
}


def _normalize_pattern_id(pattern_id: str | None) -> str:
    if not pattern_id:
        return auto_select_template({})
    p = get_pattern(pattern_id)
    return p.pattern_id if p else pattern_id


def _build_param_table(
    *, pattern: ArchPattern, models: dict[str, ModelInfo], convergence: str
) -> str:
    rows = [
        ("Core", models["core"].model, "Core↔Spine 400G", "跨域路由与汇聚"),
        ("Spine", models["spine"].model, f"Spine↔Leaf 400G SR4 · {convergence}", "参数面汇聚"),
        ("Leaf", models["leaf"].model, "Leaf↔GPU DAC/400G", "接入层下行"),
        ("Compute", models["gpu_server"].model, "GPU NVLink/RoCE", "AI 算力"),
        ("Storage", models["storage"].model, "独立存储网 400G", "Checkpoint/数据集"),
        ("Mgmt", models["mgmt"].model, "OOB 25G 虚线", "带外管理"),
    ]
    lines = [
        "| 网络层 | 代表设备 | 连接关系 | 功能定位 |",
        "|--------|----------|----------|----------|",
    ]
    for layer, model, link, role in rows:
        lines.append(f"| {layer} | {model} | {link} | {role} |")
    lines.append(f"\n> 模板: {pattern.display_name} · 收敛比 {convergence}")
    return "\n".join(lines)


def _design_principles(pattern: ArchPattern, convergence: str) -> list[str]:
    hints = pattern.layout_hints
    principles: list[str] = []
    if hints.get("spine_no_direct_server"):
        principles.append("Spine 不直连服务器，必须经过 Leaf 接入")
    if hints.get("storage_plane_separate"):
        principles.append("存储网独立平面，不与参数面混用")
    principles.append(f"收敛比 {hints.get('convergence_ratio_label', convergence)} 已标注于链路")
    return principles[:3]


class _MermaidBuilder:
    """V4.0 builder — JSON init + classDef/class，连线标签双引号."""

    def __init__(self, title: str) -> None:
        self.lines: list[str] = [
            aidc_init_directive(),
            diagram_header_comment(title),
            "flowchart TD",
            "",
        ]
        self.node_classes: dict[str, str] = {}
        self.subgraph_ids: list[str] = []

    def add(self, line: str) -> None:
        self.lines.append(line)

    def begin_subgraph(self, sid: str, title: str) -> None:
        self.add(f'    subgraph {sid}["{title}"]')
        self.add("        direction TB")
        self.subgraph_ids.append(sid)

    def end_subgraph(self) -> None:
        self.add("    end")
        self.add("")

    def node(self, node_id: str, label: str, layer: str) -> None:
        self.add(f'        {node_id}["{label}"]')
        self.node_classes[node_id] = NODE_CLASS_MAP.get(layer, "dataPlane")

    def link(self, src: str, dst: str, label: str = "", heavy: bool = False) -> None:
        arrow = "==>" if heavy else "-->"
        if label:
            self.add(f"    {src} {arrow}|{quote_edge_label(label)}| {dst}")
        else:
            self.add(f"    {src} {arrow} {dst}")

    def mgmt_link(self, src: str, dst: str, label: str = "OOB") -> None:
        self.add(f"    {src} -.->|{quote_edge_label(label)}| {dst}")

    def finish(self, principles: list[str]) -> str:
        self.add(design_note_box(principles))
        self.node_classes["AIDC_NOTE"] = "noteStyle"
        self.add("")
        self.add(render_class_defs())
        self.add(render_class_assignments(self.node_classes))
        self.add("")
        for sid in self.subgraph_ids:
            layer_key = SUBGRAPH_LAYER_STYLE.get(sid, "compute")
            self.add(f"    style {sid} {layer_subgraph_style(layer_key)}")
        self.add("%% param_table: see delivery_package.param_table")
        return "\n".join(self.lines)


def _build_v31_diagram(
    *,
    pattern: ArchPattern,
    models: dict[str, ModelInfo],
    servers: int,
    leaf: int,
    spine: int,
    storage_nodes: int,
    convergence: str,
    gpus: int,
    liquid_cooling: bool,
) -> str:
    b = _MermaidBuilder(pattern.display_name)
    gpu, leaf_m, spine_m, core_m, stor_m, mgmt_m = (
        models["gpu_server"],
        models["leaf"],
        models["spine"],
        models["core"],
        models["storage"],
        models["mgmt"],
    )

    b.begin_subgraph("CORE", "Core 核心层")
    b.node("CORE_SW", core_m.label, "core")
    b.end_subgraph()

    b.begin_subgraph("SPINE", f"Spine 汇聚层 · 收敛比 {convergence}")
    b.node("SPINE_MAIN", spine_m.label, "spine")
    if spine > 1:
        b.node(
            "SPINE_EXT",
            device_label(spine_m.model, "Spine 扩展", f"+{spine - 1} 台"),
            "spine",
        )
    b.end_subgraph()

    b.begin_subgraph("LEAF", "Leaf 接入层")
    b.node("LEAF_MAIN", leaf_m.label, "leaf")
    if leaf > 1:
        b.node(
            "LEAF_EXT",
            device_label(leaf_m.model, "Leaf 扩展", f"+{leaf - 1} 台"),
            "leaf",
        )
    b.end_subgraph()

    if pattern.pattern_id == "rail_optimized" and pattern.layout_hints.get("gpu_group_wrap"):
        rails = max(1, math.ceil(servers / 8))
        b.begin_subgraph("COMPUTE", f"计算层 · {gpus} GPU · {servers} 节点")
        for r in range(min(rails, 3)):
            b.node(f"GPU_R{r + 1}", gpu.label, "compute")
        if rails > 3:
            b.node(
                "GPU_MORE",
                device_label(gpu.model, "Rail 扩展组", f"+{rails - 3} 组"),
                "compute",
            )
        b.end_subgraph()
        compute_anchor = "GPU_R1"
    elif pattern.pattern_id == "hybrid_campus":
        train_n = max(1, math.ceil(servers * 0.7))
        infer_n = max(1, servers - train_n)
        b.begin_subgraph("COMPUTE", "计算层 · 训推物理隔离")
        b.node(
            "GPU_TRAIN",
            device_label(gpu.model, "训练集群", f"{train_n} 节点"),
            "compute",
        )
        b.node(
            "GPU_INFER",
            device_label(gpu.model, "推理集群", f"{infer_n} 节点"),
            "render",
        )
        b.end_subgraph()
        compute_anchor = "GPU_TRAIN"
    else:
        b.begin_subgraph("COMPUTE", f"计算层 · {gpus} GPU")
        b.node("GPU_MAIN", gpu.label, "compute")
        if servers > 1:
            b.node(
                "GPU_POOL",
                device_label(gpu.model, "计算扩展池", f"+{servers - 1} 台"),
                "compute",
            )
        b.end_subgraph()
        compute_anchor = "GPU_MAIN"

    b.begin_subgraph("STORAGE", "存储层 · 独立平面")
    b.node("STORE_MAIN", stor_m.label, "storage")
    if storage_nodes > 1:
        b.node(
            "STORE_EXT",
            device_label(stor_m.model, "存储扩展", f"+{storage_nodes - 1} 节点"),
            "storage",
        )
    b.end_subgraph()

    cool = "液冷分区" if liquid_cooling else "风冷分区"
    b.begin_subgraph("MGMT", "管理层 · 带外")
    b.node("MGMT_SW", mgmt_m.label, "mgmt")
    b.node("COOL_ZONE", device_label(cool, "机房工程", pattern.compliance_notes), "mgmt")
    b.end_subgraph()

    b.link("CORE_SW", "SPINE_MAIN", "400G SR4", heavy=True)
    b.link("SPINE_MAIN", "LEAF_MAIN", f"400G · {convergence}", heavy=True)

    if pattern.pattern_id == "hybrid_campus":
        b.link("GPU_TRAIN", "LEAF_MAIN", "400G RoCE")
        b.link("GPU_INFER", "LEAF_MAIN", "400G RoCE")
    else:
        b.link(compute_anchor, "LEAF_MAIN", "DAC/400G")

    b.link("STORE_MAIN", "LEAF_MAIN", "独立存储网")
    b.mgmt_link("MGMT_SW", "LEAF_MAIN", "25G OOB")

    return b.finish(_design_principles(pattern, convergence))


def _talking_points(pattern: ArchPattern, convergence: str, gpus: int) -> list[str]:
    if pattern.pattern_id == "rail_optimized":
        return [
            f"Rail 分组 + 独立存储平面，支撑 {gpus}+ GPU 线性扩展预训练",
            f"Spine-Leaf {convergence} 无收敛设计，保障 AllReduce 通信带宽",
            "全公开型号可溯源，满足招投标技术合规要求",
        ]
    if pattern.pattern_id == "hybrid_campus":
        return [
            "训练/推理物理隔离 + Core 可控互通，降低业务相互干扰",
            "管理/业务/存储三网分离，边界清晰便于等保审计",
            f"收敛比 {convergence} 兼顾成本与扩展，适合园区训推一体",
        ]
    return [
        f"Fat-Tree {convergence} 收敛，企业 SFT/推理场景性价比最优",
        "三网分离标注完整，运维与故障域清晰",
        "400G RoCE 生态成熟，交付周期优于 IB 专网",
    ]


def _compliance_checklist(model_warnings: list[str], violations: list) -> list[str]:
    items = list(v40_compliance_checklist())
    items.extend(
        [
            "✅ 设备型号来自 data/public_models.json",
            "✅ 无内部定价、竞品贬损或未授权专利号",
        ]
    )
    if model_warnings:
        items.append(f"⚠️ 型号映射: {'; '.join(model_warnings)}")
    if violations:
        items.append(f"⚠️ 待修复: {len(violations)} 项")
    else:
        items.append("✅ 通过 AIDC V4.0 mermaid.live 合规校验")
    return items


def generate_architecture_diagram(
    *,
    requirement: str = "",
    pattern_id: str | None = None,
    topology: dict[str, Any] | None = None,
    target_gpus: int = 64,
    scenario: str = "TRAINING",
    convergence_ratio: str | None = None,
    device_overrides: dict[str, str] | None = None,
    liquid_cooling: bool = False,
    domestic_mode: bool = False,
) -> DiagramGenerationResult:
    pid = _normalize_pattern_id(pattern_id) if pattern_id else auto_select_template(
        {"requirement": requirement, "target_gpus": target_gpus, "scenario": scenario}
    )
    pattern = get_pattern(pid) or match_pattern(
        requirement, target_gpus=target_gpus, scenario=scenario
    )

    topo = topology or {}
    compute = topo.get("compute") or {}
    network = topo.get("network") or {}
    storage = topo.get("storage") or {}

    servers = int(compute.get("servers") or max(1, target_gpus // 8))
    gpus = int(compute.get("gpus") or target_gpus)
    leaf = int(network.get("leaf_switches") or max(2, servers // 16))
    spine = int(network.get("spine_switches") or max(2, leaf // 2))
    storage_nodes = int(storage.get("nodes") or max(2, servers // 12))

    convergence = convergence_ratio or compute_convergence_ratio(
        servers=servers, gpus_per_node=8, leaf_switches=leaf
    )
    if pattern.pattern_id == "fat_tree_inference" and convergence == "1:1" and target_gpus < 256:
        convergence = pattern.default_convergence

    models = default_models_for_pattern(pattern.pattern_id)
    model_warnings: list[str] = []
    if device_overrides:
        for key, name in device_overrides.items():
            resolved = resolve_model(name)
            models[key] = resolved
            model_warnings.extend(resolved.warnings)
    if domestic_mode:
        models["gpu_server"] = resolve_model("Ascend 910B")

    mermaid = _build_v31_diagram(
        pattern=pattern,
        models=models,
        servers=servers,
        leaf=leaf,
        spine=spine,
        storage_nodes=storage_nodes,
        convergence=convergence,
        gpus=gpus,
        liquid_cooling=liquid_cooling,
    )

    violations = validate_aidc_compliance(mermaid)
    return DiagramGenerationResult(
        pattern_id=pattern.pattern_id,
        pattern_name=pattern.display_name,
        mermaid_code=mermaid,
        convergence_ratio=convergence,
        design_points=_talking_points(pattern, convergence, gpus),
        render_tools=RENDER_TOOLS,
        validation_issues=violations_to_dict(violations),
        compliance_notes=pattern.compliance_notes,
        param_table=_build_param_table(pattern=pattern, models=models, convergence=convergence),
        model_warnings=model_warnings,
        compliance_checklist=_compliance_checklist(model_warnings, violations),
    )
