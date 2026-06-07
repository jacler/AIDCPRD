"""Spine-Leaf topology SVG — compute plane vs storage plane, optics, convergence."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OPTICS_PATH = _REPO_ROOT / "data" / "public_sources" / "optics" / "transceiver_types.json"


@dataclass
class OpticLink:
    from_node: str
    to_node: str
    optic_type: str
    label: str
    fiber_type: str | None
    direction: str


@dataclass
class TopologyRenderResult:
    compute_svg: str
    storage_svg: str
    convergence_ratio: str
    compute_links: list[OpticLink] = field(default_factory=list)
    storage_links: list[OpticLink] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _load_optics_catalog() -> list[dict[str, Any]]:
    if not _OPTICS_PATH.is_file():
        return []
    return json.loads(_OPTICS_PATH.read_text(encoding="utf-8")).get("modules", [])


def _optic_by_type(catalog: list[dict[str, Any]], optic_type: str) -> dict[str, Any]:
    for item in catalog:
        if item.get("type") == optic_type:
            return item
    return {"type": optic_type, "label": optic_type, "fiber_type": None}


def compute_convergence_ratio(
    *,
    servers: int,
    gpus_per_node: int,
    leaf_switches: int,
    switch_ports: int = 64,
) -> str:
    """Downlink : uplink oversubscription per leaf tier (deterministic)."""
    if leaf_switches <= 0 or switch_ports < 2:
        return "N/A"
    down_per_leaf = switch_ports // 2
    up_per_leaf = switch_ports - down_per_leaf
    total_down = servers * gpus_per_node
    down_per_leaf_actual = math.ceil(total_down / leaf_switches)
    if down_per_leaf_actual <= up_per_leaf:
        return "1:1"
    ratio = down_per_leaf_actual / max(up_per_leaf, 1)
    if ratio <= 1.05:
        return "1:1"
    if ratio <= 2.1:
        return "2:1"
    if ratio <= 3.1:
        return "3:1"
    return f"{math.ceil(ratio)}:1"


def _classify_leaf_spine_optic(leaf_count: int, spine_count: int) -> str:
    """Intra-DC SR4 by default; LR4 when fabric spans many spine tiers."""
    if leaf_count * spine_count > 48:
        return "LR4"
    return "SR4"


def _build_compute_links(
    *,
    servers: int,
    leaf_switches: int,
    spine_switches: int,
    optics_catalog: list[dict[str, Any]],
) -> list[OpticLink]:
    links: list[OpticLink] = []
    dac = _optic_by_type(optics_catalog, "DAC")
    spine_optic_type = _classify_leaf_spine_optic(leaf_switches, spine_switches)
    spine_optic = _optic_by_type(optics_catalog, spine_optic_type)

    visible_servers = min(servers, 8)
    for i in range(visible_servers):
        leaf_idx = i % max(leaf_switches, 1)
        links.append(
            OpticLink(
                from_node=f"C{i + 1}",
                to_node=f"L{leaf_idx + 1}",
                optic_type="DAC",
                label=str(dac.get("label", "DAC")),
                fiber_type=dac.get("fiber_type"),
                direction="server→leaf",
            )
        )

    visible_leaf = min(leaf_switches, 6)
    for i in range(visible_leaf):
        spine_idx = i % max(spine_switches, 1)
        links.append(
            OpticLink(
                from_node=f"L{i + 1}",
                to_node=f"S{spine_idx + 1}",
                optic_type=spine_optic_type,
                label=str(spine_optic.get("label", spine_optic_type)),
                fiber_type=spine_optic.get("fiber_type"),
                direction="leaf→spine (MMF/SMF)",
            )
        )
    return links


def _build_storage_links(
    *,
    storage_nodes: int,
    leaf_switches: int,
    optics_catalog: list[dict[str, Any]],
) -> list[OpticLink]:
    links: list[OpticLink] = []
    sr4 = _optic_by_type(optics_catalog, "SR4")
    visible = min(storage_nodes, 6)
    for i in range(visible):
        leaf_idx = i % max(leaf_switches, 1)
        links.append(
            OpticLink(
                from_node=f"ST{i + 1}",
                to_node=f"L{leaf_idx + 1}",
                optic_type="SR4",
                label=str(sr4.get("label", "SR4")),
                fiber_type=sr4.get("fiber_type"),
                direction="storage→leaf (独立存储网)",
            )
        )
    return links


def _svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _draw_plane_svg(
    *,
    title: str,
    plane_color: str,
    spine_count: int,
    leaf_count: int,
    bottom_nodes: int,
    bottom_prefix: str,
    bottom_label: str,
    convergence_ratio: str,
    links: list[OpticLink],
    width: int = 720,
    height: int = 340,
) -> str:
    spine_y, leaf_y, bottom_y = 48, 130, 230
    spine_xs = _row_x(spine_count, 90, width // 2, min(72, width // max(spine_count, 1)))
    leaf_xs = _row_x(leaf_count, 70, width // 2, min(56, width // max(leaf_count, 1)))
    bottom_xs = _row_x(bottom_nodes, 60, width // 2, min(48, width // max(bottom_nodes, 1)))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="16" y="24" font-size="14" font-weight="600" fill="#0f172a">{_svg_escape(title)}</text>',
        f'<text x="16" y="42" font-size="11" fill="#475569">收敛比 {convergence_ratio} · Spine-Leaf</text>',
    ]

    for i, x in enumerate(spine_xs):
        parts.append(_node_box(x, spine_y, f"S{i + 1}", plane_color, 36, 28))
    for i, x in enumerate(leaf_xs):
        parts.append(_node_box(x, leaf_y, f"L{i + 1}", "#e2e8f0", 36, 28))
    visible_bottom = min(bottom_nodes, len(bottom_xs))
    for i in range(visible_bottom):
        parts.append(_node_box(bottom_xs[i], bottom_y, f"{bottom_prefix}{i + 1}", "#fff", 32, 24))

    if bottom_nodes > visible_bottom:
        parts.append(
            f'<text x="{width // 2}" y="{bottom_y + 40}" text-anchor="middle" '
            f'font-size="10" fill="#64748b">+{bottom_nodes - visible_bottom} {_svg_escape(bottom_label)}</text>'
        )

    for link in links[:12]:
        parts.append(
            f'<text x="16" y="{height - 80 + links.index(link) * 14}" font-size="9" fill="#334155">'
            f'{_svg_escape(link.from_node)} → {_svg_escape(link.to_node)}: '
            f'{_svg_escape(link.label)} ({_svg_escape(link.direction)})</text>'
        )

    parts.append(
        f'<text x="16" y="{height - 12}" font-size="9" fill="#94a3b8">'
        f'数据来源: data/public_sources/optics/transceiver_types.json</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _row_x(count: int, spacing: int, center: int, max_spacing: int) -> list[int]:
    if count <= 0:
        return []
    gap = min(spacing, max_spacing)
    total = (count - 1) * gap
    start = center - total // 2
    return [start + i * gap for i in range(count)]


def _node_box(x: int, y: int, label: str, fill: str, w: int, h: int) -> str:
    return (
        f'<rect x="{x - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" rx="4" '
        f'fill="{fill}" stroke="#94a3b8" stroke-width="1"/>'
        f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-size="10" fill="#0f172a">'
        f'{_svg_escape(label)}</text>'
    )


def render_topology_svgs(
    topology: dict[str, Any],
    *,
    gpus_per_node: int = 8,
    switch_ports: int = 64,
    convergence_ratio: str | None = None,
) -> TopologyRenderResult:
    """Render compute and storage network SVG diagrams from topology JSON."""
    compute = topology.get("compute") or {}
    network = topology.get("network") or {}
    storage = topology.get("storage") or {}

    servers = int(compute.get("servers") or 1)
    gpus = int(compute.get("gpus") or servers * gpus_per_node)
    leaf = int(network.get("leaf_switches") or max(2, servers // 16))
    spine = int(network.get("spine_switches") or max(2, leaf // 2))
    storage_nodes = int(storage.get("nodes") or max(2, servers // 12))

    ratio = convergence_ratio or compute_convergence_ratio(
        servers=servers,
        gpus_per_node=gpus_per_node,
        leaf_switches=leaf,
        switch_ports=switch_ports,
    )

    optics = _load_optics_catalog()
    compute_links = _build_compute_links(
        servers=servers,
        leaf_switches=leaf,
        spine_switches=spine,
        optics_catalog=optics,
    )
    storage_links = _build_storage_links(
        storage_nodes=storage_nodes,
        leaf_switches=leaf,
        optics_catalog=optics,
    )

    compute_svg = _draw_plane_svg(
        title="计算网 (Parameter / RDMA Plane)",
        plane_color="#dbeafe",
        spine_count=min(spine, 8),
        leaf_count=min(leaf, 8),
        bottom_nodes=servers,
        bottom_prefix="C",
        bottom_label="计算节点",
        convergence_ratio=ratio,
        links=compute_links,
    )
    storage_svg = _draw_plane_svg(
        title="存储网 (Storage Plane — 独立于计算网)",
        plane_color="#dcfce7",
        spine_count=min(max(2, spine // 2), 4),
        leaf_count=min(max(2, leaf // 2), 6),
        bottom_nodes=storage_nodes,
        bottom_prefix="ST",
        bottom_label="存储节点",
        convergence_ratio="1:1",
        links=storage_links,
    )

    return TopologyRenderResult(
        compute_svg=compute_svg,
        storage_svg=storage_svg,
        convergence_ratio=ratio,
        compute_links=compute_links,
        storage_links=storage_links,
        metadata={
            "servers": servers,
            "gpus": gpus,
            "leaf_switches": leaf,
            "spine_switches": spine,
            "storage_nodes": storage_nodes,
        },
    )
