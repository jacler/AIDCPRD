"""Multi-format architecture diagram export — PPT / Word / Web."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.visualizer.diagram_generator import DiagramGenerationResult


class ExportMode(str, Enum):
    PPT_READY = "ppt_ready"
    DOC_EMBED = "doc_embed"
    WEB_INTERACTIVE = "web_interactive"


@dataclass
class DiagramExportBundle:
    mode: str
    mermaid_code: str
    figure_caption: str
    design_points: list[str]
    speaker_notes: str
    export_hints: dict[str, Any]
    data_disclaimer: str
    svg_wrapper: str | None = None


def _figure_caption(result: DiagramGenerationResult, figure_no: str = "3-2") -> str:
    return f"图{figure_no} {result.pattern_name}（收敛比 {result.convergence_ratio}）"


def _speaker_notes(result: DiagramGenerationResult) -> str:
    bullets = "\n".join(f"• {p}" for p in result.design_points[:3])
    return (
        f"{result.pattern_name}\n\n"
        f"设计要点：\n{bullets}\n\n"
        f"{result.data_disclaimer}\n"
        f"合规：{result.compliance_notes}"
    )


def export_diagram(
    result: DiagramGenerationResult,
    mode: ExportMode | str = ExportMode.WEB_INTERACTIVE,
    *,
    figure_no: str = "3-2",
) -> DiagramExportBundle:
    """Adapt Mermaid code for PPT / Word / Web delivery."""
    mode_val = ExportMode(mode) if isinstance(mode, str) else mode
    caption = _figure_caption(result, figure_no)
    notes = _speaker_notes(result)

    if mode_val == ExportMode.PPT_READY:
        code = _wrap_ppt(result.mermaid_code, caption)
        hints = {
            "aspect_ratio": "16:9",
            "min_font_pt": 12,
            "dpi": 300,
            "contrast": "high",
            "tool": "VS Code Mermaid Preview → Export PNG 300dpi",
            "size": "1920x1080 recommended",
        }
        return DiagramExportBundle(
            mode=mode_val.value,
            mermaid_code=code,
            figure_caption=caption,
            design_points=result.design_points,
            speaker_notes=notes,
            export_hints=hints,
            data_disclaimer=result.data_disclaimer,
        )

    if mode_val == ExportMode.DOC_EMBED:
        svg = _svg_wrapper(result, caption)
        code = result.mermaid_code
        hints = {
            "format": "SVG/PDF vector",
            "page": "A4 portrait",
            "figure_number": figure_no,
            "tool": "Mermaid Live → Export SVG, embed in Word",
        }
        return DiagramExportBundle(
            mode=mode_val.value,
            mermaid_code=code,
            figure_caption=caption,
            design_points=result.design_points,
            speaker_notes=notes,
            export_hints=hints,
            data_disclaimer=result.data_disclaimer,
            svg_wrapper=svg,
        )

    code = _wrap_web(result.mermaid_code, result)
    hints = {
        "compatible": "Mermaid Live Editor",
        "responsive": True,
        "interactive": "Click subgraph comments in %% metadata",
        "tool": "https://mermaid.live",
        "pattern_id": result.pattern_id,
        "convergence_ratio": result.convergence_ratio,
    }
    return DiagramExportBundle(
        mode=mode_val.value,
        mermaid_code=code,
        figure_caption=caption,
        design_points=result.design_points,
        speaker_notes=notes,
        export_hints=hints,
        data_disclaimer=result.data_disclaimer,
    )


def _insert_after_preamble(mermaid: str, insert: str) -> str:
    """V4.0: 注释放在 init 指令或 frontmatter 之后."""
    m = re.match(r"^(%%\{init:.*?\}%%\s*\n)(.*)", mermaid, re.DOTALL)
    if m:
        return m.group(1) + insert + m.group(2)
    m = re.match(r"^(---\s*\n.*?\n---\n)(.*)", mermaid, re.DOTALL)
    if m:
        return m.group(1) + insert + m.group(2)
    return insert + mermaid


def _wrap_ppt(mermaid: str, caption: str) -> str:
    header = f"%% PPT_READY 16:9 · {caption} · min 12pt · 300dpi export\n"
    if "%%{init:" not in mermaid:
        return header + mermaid
    code = mermaid.replace('"fontSize":"14px"', '"fontSize":"16px"')
    return _insert_after_preamble(code, header)


def _wrap_web(mermaid: str, result: DiagramGenerationResult) -> str:
    """V4.0: 禁止在 --- 之前插入任何字符，否则 mermaid.live YAML 解析失败."""
    return mermaid


def _svg_wrapper(result: DiagramGenerationResult, caption: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="794" height="1123" viewBox="0 0 794 1123">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<text x="397" y="40" text-anchor="middle" font-size="14" font-weight="bold">{caption}</text>'
        f'<foreignObject x="40" y="60" width="714" height="1000">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="font-size:10px">'
        f"<!-- Render Mermaid to SVG via Mermaid CLI / Live Editor --></div>"
        f"</foreignObject>"
        f'<text x="397" y="1100" text-anchor="middle" font-size="8" fill="#888">{result.data_disclaimer}</text>'
        f"</svg>"
    )
