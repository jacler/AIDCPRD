"""Rack cabinet layout SVG — U placement, PDU, cooling, power density warnings."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RACK_PATH = _REPO_ROOT / "data" / "public_sources" / "racks" / "standard_42u.json"
_SERVER_PATH = _REPO_ROOT / "data" / "public_sources" / "servers" / "gpu_node_8x.json"
_GPU_DEFAULT_TDP = 700.0  # from data/public_sources/gpus — H100 class reference


@dataclass
class RackPlacement:
    rack_id: int
    servers: list[dict[str, Any]]
    total_u: int
    power_kw: float
    over_power_limit: bool
    cooling: str


@dataclass
class CabinetLayoutResult:
    svg: str
    racks: list[RackPlacement]
    total_racks: int
    total_power_kw: float
    power_limit_kw_per_rack: float
    cooling_method: str
    warnings: list[str] = field(default_factory=list)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _estimate_server_power_kw(gpus_per_node: int, gpu_tdp_w: float, overhead_w: float) -> float:
    return round((gpus_per_node * gpu_tdp_w + overhead_w) / 1000.0, 2)


def plan_rack_layout(
    *,
    server_count: int,
    gpus_per_node: int = 8,
    gpu_tdp_w: float | None = None,
) -> CabinetLayoutResult:
    """Pack servers into 42U racks with power density checks."""
    rack_spec = _load_json(_RACK_PATH)
    server_spec = _load_json(_SERVER_PATH)

    rack_u = int((rack_spec.get("specs") or {}).get("rack_units") or 42)
    server_u = int((server_spec.get("specs") or {}).get("rack_units") or 4)
    overhead_w = float((server_spec.get("specs") or {}).get("platform_overhead_w") or 500)
    cooling = str((server_spec.get("specs") or {}).get("cooling") or "air")
    specs = rack_spec.get("specs") or {}
    power_limit = float(
        specs.get("usable_power_kw_liquid" if cooling == "liquid" else "usable_power_kw_air") or 15.0
    )

    tdp = gpu_tdp_w if gpu_tdp_w is not None else _GPU_DEFAULT_TDP
    server_kw = _estimate_server_power_kw(gpus_per_node, tdp, overhead_w)
    max_servers_per_rack_u = max(1, (rack_u - 4) // server_u)  # reserve 4U for PDU/switch
    max_servers_by_power = max(1, int(power_limit // server_kw))
    servers_per_rack = min(max_servers_per_rack_u, max_servers_by_power)

    racks: list[RackPlacement] = []
    warnings: list[str] = []
    remaining = server_count
    rack_id = 1

    while remaining > 0:
        batch = min(remaining, servers_per_rack)
        used_u = batch * server_u + 4
        power = round(batch * server_kw, 2)
        over = power > power_limit
        if over:
            warnings.append(f"机柜 R{rack_id} 功率 {power}kW 超过 {power_limit}kW 预警线")
        servers = [
            {"id": f"S{server_count - remaining + i + 1}", "u_start": rack_u - 2 - (i + 1) * server_u, "u_height": server_u}
            for i in range(batch)
        ]
        racks.append(
            RackPlacement(
                rack_id=rack_id,
                servers=servers,
                total_u=used_u,
                power_kw=power,
                over_power_limit=over,
                cooling=cooling,
            )
        )
        remaining -= batch
        rack_id += 1

    if not racks and server_count == 0:
        racks.append(
            RackPlacement(rack_id=1, servers=[], total_u=0, power_kw=0.0, over_power_limit=False, cooling=cooling)
        )

    total_power = round(sum(r.power_kw for r in racks), 2)
    svg = _render_racks_svg(racks, rack_u=rack_u, power_limit=power_limit, cooling=cooling)

    return CabinetLayoutResult(
        svg=svg,
        racks=racks,
        total_racks=len(racks),
        total_power_kw=total_power,
        power_limit_kw_per_rack=power_limit,
        cooling_method=cooling,
        warnings=warnings,
    )


def _render_racks_svg(
    racks: list[RackPlacement],
    *,
    rack_u: int,
    power_limit: float,
    cooling: str,
) -> str:
    rack_w, rack_h = 100, 420
    gap = 24
    margin = 20
    width = margin * 2 + len(racks) * rack_w + max(0, len(racks) - 1) * gap
    height = rack_h + 120

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="20" y="22" font-size="14" font-weight="600" fill="#0f172a">机柜排布视图</text>',
        f'<text x="20" y="40" font-size="11" fill="#475569">'
        f'{rack_u}U 标准机柜 · 制冷: {cooling} · 功率密度预警线 {power_limit} kW/柜</text>',
    ]

    u_px = rack_h / rack_u
    warning_y = margin + 50 + rack_h - int(power_limit / 20 * rack_u) * u_px * 0.15

    for idx, rack in enumerate(racks):
        x = margin + idx * (rack_w + gap)
        y = margin + 50
        stroke = "#ef4444" if rack.over_power_limit else "#334155"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{rack_w}" height="{rack_h}" fill="#fff" '
            f'stroke="{stroke}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + rack_w // 2}" y="{y - 8}" text-anchor="middle" font-size="11" '
            f'font-weight="600" fill="#0f172a">R{rack.rack_id}</text>'
        )
        parts.append(
            f'<text x="{x + rack_w // 2}" y="{y + rack_h + 16}" text-anchor="middle" font-size="9" '
            f'fill="#64748b">{rack.power_kw} kW</text>'
        )

        # PDU at bottom rear
        pdu_h = 4 * u_px
        parts.append(
            f'<rect x="{x + 4}" y="{y + rack_h - pdu_h - 4}" width="{rack_w - 8}" height="{pdu_h}" '
            f'fill="#fef3c7" stroke="#d97706" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x + rack_w // 2}" y="{y + rack_h - pdu_h // 2}" text-anchor="middle" '
            f'font-size="8" fill="#92400e">PDU</text>'
        )

        for srv in rack.servers:
            u_start = int(srv["u_start"])
            u_height = int(srv["u_height"])
            sy = y + rack_h - (u_start + u_height) * u_px
            sh = u_height * u_px - 2
            parts.append(
                f'<rect x="{x + 8}" y="{sy}" width="{rack_w - 16}" height="{sh}" '
                f'fill="#dbeafe" stroke="#3b82f6" stroke-width="1" rx="2"/>'
            )
            parts.append(
                f'<text x="{x + rack_w // 2}" y="{sy + sh // 2 + 3}" text-anchor="middle" '
                f'font-size="8" fill="#1e40af">{_svg_escape(str(srv["id"]))}</text>'
            )

        # Power density warning line
        warn_line_y = y + rack_h * 0.35
        parts.append(
            f'<line x1="{x}" y1="{warn_line_y}" x2="{x + rack_w}" y2="{warn_line_y}" '
            f'stroke="#f59e0b" stroke-width="1" stroke-dasharray="4,3"/>'
        )

    parts.append(
        f'<text x="20" y="{height - 24}" font-size="9" fill="#94a3b8">'
        f'数据来源: data/public_sources/racks/standard_42u.json, servers/gpu_node_8x.json</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_cabinet_layout_svg(
    topology: dict[str, Any],
    *,
    gpus_per_node: int = 8,
    gpu_tdp_w: float | None = None,
) -> CabinetLayoutResult:
    compute = topology.get("compute") or {}
    servers = int(compute.get("servers") or 1)
    return plan_rack_layout(
        server_count=servers,
        gpus_per_node=gpus_per_node,
        gpu_tdp_w=gpu_tdp_w,
    )
