"""AIDC V3.0 delivery package — diagram + table + talking points + compliance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.export.diagram_exporter import ExportMode, export_diagram
from app.visualizer.aidc_golden_rules import sanitize_mermaid_for_render
from app.visualizer.diagram_generator import DiagramGenerationResult, generate_architecture_diagram


COMPLIANCE_STATEMENT = (
    "本图基于公开技术参数生成，仅供技术参考，不构成商业承诺"
)

RENDER_GUIDE = {
    "tools": [
        {"name": "Mermaid Live Editor", "url": "https://mermaid.live", "params": "Export PNG 300dpi"},
        {"name": "Typora", "params": "导出 PDF/SVG 矢量"},
        {"name": "VS Code Mermaid Preview", "params": "Export PNG 300dpi, 16:9"},
    ],
    "dpi": 300,
    "formats": ["PNG", "SVG", "PDF"],
}


@dataclass
class DeliveryPackage:
    mermaid_code: str
    param_table: str
    talking_points: list[str]
    compliance_statement: str
    compliance_checklist: list[str]
    render_guide: dict[str, Any]
    pattern_id: str
    pattern_name: str
    convergence_ratio: str
    figure_caption: str
    validation_issues: list[dict[str, Any]] = field(default_factory=list)
    model_warnings: list[str] = field(default_factory=list)
    render_tools: list[dict[str, str]] = field(default_factory=list)
    export_mode: str = "web_interactive"
    export_hints: dict[str, Any] = field(default_factory=dict)


def build_delivery_package(
    result: DiagramGenerationResult,
    *,
    export_mode: str = "web_interactive",
    figure_no: str = "3-2",
) -> DeliveryPackage:
    bundle = export_diagram(result, export_mode, figure_no=figure_no)
    caption = bundle.figure_caption

    return DeliveryPackage(
        mermaid_code=sanitize_mermaid_for_render(bundle.mermaid_code),
        param_table=result.param_table,
        talking_points=result.design_points[:3],
        compliance_statement=COMPLIANCE_STATEMENT,
        compliance_checklist=result.compliance_checklist,
        render_guide={**RENDER_GUIDE, "export_hints": bundle.export_hints},
        pattern_id=result.pattern_id,
        pattern_name=result.pattern_name,
        convergence_ratio=result.convergence_ratio,
        figure_caption=caption,
        validation_issues=result.validation_issues,
        model_warnings=result.model_warnings,
        render_tools=result.render_tools,
        export_mode=bundle.mode,
        export_hints=bundle.export_hints,
    )


def generate_delivery_package(
    *,
    requirement: str = "",
    pattern_id: str | None = None,
    topology: dict[str, Any] | None = None,
    target_gpus: int = 64,
    scenario: str = "TRAINING",
    export_mode: str = "ppt_ready",
    figure_no: str = "3-2",
    **kwargs: Any,
) -> DeliveryPackage:
    result = generate_architecture_diagram(
        requirement=requirement,
        pattern_id=pattern_id,
        topology=topology,
        target_gpus=target_gpus,
        scenario=scenario,
        **kwargs,
    )
    return build_delivery_package(result, export_mode=export_mode, figure_no=figure_no)
