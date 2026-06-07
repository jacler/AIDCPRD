"""Engineering visual style guide — GB/T 51380-2019 aligned color & typography rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# All diagram colors must reference these tokens — no ad-hoc hex in generators
COLORS: dict[str, dict[str, str]] = {
    "compute": {"fill": "#E6F7FF", "border": "#91D5FF"},
    "network": {"fill": "#F6FFED", "border": "#B7EB8F"},
    "storage": {"fill": "#FFF7E6", "border": "#FFD591"},
    "management": {"fill": "#F9F0FF", "border": "#D3ADF7"},
    "core": {"fill": "#E6FFFB", "border": "#87E8DE"},
}

FONTS: dict[str, str] = {
    "title": "14pt Bold",
    "device_label": "10pt Regular",
    "link_label": "8pt Italic",
}

LINK_RULES: dict[str, str] = {
    "data": "solid arrow",
    "management": "dashed line",
    "alignment_tolerance_px": "5",
    "cross_tier": "vertical preferred",
}

REDUNDANT_PHRASES: tuple[str, ...] = (
    "server to leaf connection",
    "this is a",
    "click here",
    "placeholder",
    "todo",
)

MERMAID_CLASS_DEFS = "\n".join(
    [
        "    classDef compute fill:#E6F7FF,stroke:#91D5FF,stroke-width:2px,color:#003A8C",
        "    classDef network fill:#F6FFED,stroke:#B7EB8F,stroke-width:2px,color:#135200",
        "    classDef storage fill:#FFF7E6,stroke:#FFD591,stroke-width:2px,color:#873800",
        "    classDef mgmt fill:#F9F0FF,stroke:#D3ADF7,stroke-width:2px,color:#391085",
        "    classDef core fill:#E6FFFB,stroke:#87E8DE,stroke-width:2px,color:#006D75",
    ]
)


@dataclass
class DiagramIssue:
    severity: str  # error | warn | info
    code: str
    message: str
    fix_hint: str


def style_frontmatter(title: str) -> str:
    from app.visualizer.aidc_golden_rules import aidc_init_directive

    return aidc_init_directive()


def validate_diagram_code(
    code: str,
    *,
    expected_convergence: str | None = None,
) -> list[DiagramIssue]:
    """Validate Mermaid diagram code against style guide."""
    issues: list[DiagramIssue] = []
    lower = code.lower()

    for phrase in REDUNDANT_PHRASES:
        if phrase in lower:
            issues.append(
                DiagramIssue(
                    severity="warn",
                    code="redundant_text",
                    message=f"包含冗余描述: \"{phrase}\"",
                    fix_hint="删除说明性废话，仅保留设备型号与链路参数",
                )
            )

    required_classes = ("classDef compute", "classDef network")
    for cls in required_classes:
        if cls not in code:
            issues.append(
                DiagramIssue(
                    severity="error",
                    code="missing_classdef",
                    message=f"缺少样式类定义: {cls}",
                    fix_hint="在 Mermaid 代码末尾追加 style_guide.MERMAID_CLASS_DEFS",
                )
            )

    if expected_convergence and expected_convergence not in code:
        issues.append(
            DiagramIssue(
                severity="error",
                code="convergence_missing",
                message=f"未标注收敛比 {expected_convergence}",
                fix_hint=f"在 Spine-Leaf 链路旁添加「收敛比 {expected_convergence}」标签",
            )
        )

    if re.search(r"fill:#[0-9a-fA-F]{6}", code):
        for token, spec in COLORS.items():
            if spec["fill"] not in code and f"classDef {token}" not in code:
                continue
    else:
        issues.append(
            DiagramIssue(
                severity="warn",
                code="no_color_tokens",
                message="未检测到 style_guide 标准色",
                fix_hint="使用 classDef compute/network/storage 标准配色",
            )
        )

    if "flowchart" not in lower and "graph" not in lower:
        issues.append(
            DiagramIssue(
                severity="error",
                code="invalid_diagram_type",
                message="非 flowchart/graph 声明式代码",
                fix_hint="使用 flowchart TB 或 LR 作为根图类型",
            )
        )

    overlap_markers = ("overlap", "文字重叠", "stacked label")
    for m in overlap_markers:
        if m in lower:
            issues.append(
                DiagramIssue(
                    severity="warn",
                    code="label_overlap_risk",
                    message="可能存在标签重叠风险",
                    fix_hint="缩短设备标签，链路标注改用 8pt 斜体独立行",
                )
            )

    return issues


def issues_to_dict(issues: list[DiagramIssue]) -> list[dict[str, Any]]:
    return [
        {
            "severity": i.severity,
            "code": i.code,
            "message": i.message,
            "fix_hint": i.fix_hint,
        }
        for i in issues
    ]
