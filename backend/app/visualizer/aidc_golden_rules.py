"""AIDC 7项黄金法则 + V4.0 Mermaid 语法合规（mermaid.live 零报错）."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

BRAND_PRIMARY = "#1890ff"
FONT_FAMILY = "Microsoft YaHei"
MIN_FONT_PT = 14

LAYER_COLORS: dict[str, dict[str, str]] = {
    "compute": {"fill": "#E6F7FF", "stroke": "#1890ff"},
    "leaf": {"fill": "#F6FFED", "stroke": "#52c41a"},
    "spine": {"fill": "#E6FFFB", "stroke": "#13c2c2"},
    "core": {"fill": "#E6FFFB", "stroke": "#13c2c2"},
    "storage": {"fill": "#FFF7E6", "stroke": "#fa8c16"},
    "mgmt": {"fill": "#FFF1F0", "stroke": "#F5222D"},
}

# 节点 classDef（替代 linkStyle 数字索引）
NODE_CLASS_DEFS: dict[str, str] = {
    "coreStyle": "fill:#E6FFFB,stroke:#13c2c2,stroke-width:2px",
    "spineStyle": "fill:#E6FFFB,stroke:#13c2c2,stroke-width:2px",
    "leafStyle": "fill:#F6FFED,stroke:#52c41a,stroke-width:2px",
    "computeStyle": "fill:#E6F7FF,stroke:#1890ff,stroke-width:2px",
    "storageStyle": "fill:#FFF7E6,stroke:#fa8c16,stroke-width:2px",
    "mgmtStyle": "fill:#F9F0FF,stroke:#722ed1,stroke-width:2px",
    "dataPlane": "fill:#fff,stroke:#722ED1,stroke-width:2px",
    "mgmtPlane": "fill:#fff,stroke:#F5222D,stroke-width:2px,stroke-dasharray:5 5",
    "storagePlane": "fill:#fff,stroke:#13C2C2,stroke-width:2px",
    "renderPlane": "fill:#fff,stroke:#FA8C16,stroke-width:4px",
    "noteStyle": "fill:#fafafa,stroke:#d9d9d9,stroke-width:1px",
}

FORBIDDEN_CONFIG_KEYS = ("rankSpacing", "nodeSpacing", "flowchart:", "curve:", "htmlLabels")

SUBGRAPH_LAYER_STYLE: dict[str, str] = {
    "CORE": "core",
    "SPINE": "spine",
    "LEAF": "leaf",
    "COMPUTE": "compute",
    "STORAGE": "storage",
    "MGMT": "mgmt",
}


@dataclass
class Violation:
    rule_id: str
    message: str
    fix_snippet: str


def aidc_init_directive(*, font_size: str | None = None) -> str:
    """V4.0: JSON init 指令 — 兼容 mermaid.live / Notion / 内嵌渲染器（禁止 YAML config）."""
    size = font_size or f"{MIN_FONT_PT}px"
    return (
        '%%{init: {"theme":"base","securityLevel":"loose",'
        f'"themeVariables":{{"primaryColor":"{BRAND_PRIMARY}","fontSize":"{size}",'
        f'"fontFamily":"{FONT_FAMILY}"}}}}%%'
    )


def aidc_frontmatter(_title: str = "") -> str:
    """向后兼容别名 — 实际输出 JSON init 指令."""
    return aidc_init_directive()


def extract_init_directive(code: str) -> str:
    m = re.search(r"%%\{init:\s*(\{.*?\})\s*\}%%", code, re.DOTALL)
    return m.group(1) if m else ""


def _strip_legacy_web_prefix(lines: list[str]) -> list[str]:
    while lines:
        s = lines[0].strip()
        if s.startswith("%% WEB_INTERACTIVE") or s.startswith("%% click"):
            lines.pop(0)
            continue
        if not s:
            lines.pop(0)
            continue
        break
    return lines


def _convert_yaml_frontmatter_to_init(text: str) -> str:
    m = re.match(r"^---\s*\n(.*?\n)---\s*\n", text, re.DOTALL)
    if not m or "config:" not in m.group(1):
        return text
    body = text[m.end() :]
    body_lines = body.splitlines()
    header = ""
    if body_lines and body_lines[0].strip().startswith("%%"):
        header = body_lines[0].rstrip() + "\n"
        body = "\n".join(body_lines[1:]).lstrip("\n")
    return f"{aidc_init_directive()}\n{header}{body}"


def _quote_all_edge_labels(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        lbl = match.group(2).strip()
        if lbl.startswith('"') and lbl.endswith('"'):
            return match.group(0)
        return f"{match.group(1)}{quote_edge_label(lbl)}{match.group(3)}"

    return re.sub(r"((?:-->|==>|-.->)\|)([^|]+)(\|)", repl, text)


def upgrade_legacy_mermaid(code: str) -> str:
    """将 V3.x 缓存代码升级为 V4.0：去 WEB 头、YAML→JSON init、连线加引号."""
    lines = _strip_legacy_web_prefix(code.strip().splitlines())
    text = _convert_yaml_frontmatter_to_init("\n".join(lines))
    return _quote_all_edge_labels(text)


def sanitize_mermaid_for_render(code: str) -> str:
    """确保可解析：升级旧格式、去除污染行与公共缩进."""
    text = upgrade_legacy_mermaid(code)
    lines = text.strip().splitlines()
    markers = ("%%{init:", "flowchart", "graph ")
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if any(line.strip().startswith(m) for m in markers)
        ),
        None,
    )
    if start is not None and start > 0:
        lines = lines[start:]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return text.strip()
    indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    if indents:
        dedent = min(indents)
        if dedent > 0:
            lines = [line[dedent:] if len(line) >= dedent else line for line in lines]
    return "\n".join(lines)


def diagram_header_comment(title: str) -> str:
    safe = title.replace("\n", " ").strip()
    return f"%% {safe}" if safe else "%% AIDC 架构图"


def quote_edge_label(label: str) -> str:
    """V4.0: 连线标签一律双引号包裹，避免 · / : 空格等触发解析错误."""
    if not label:
        return label
    safe = label.replace('"', "'")
    return f'"{safe}"'


def v40_compliance_checklist() -> list[str]:
    return [
        "[x] 使用 JSON init 指令（非 YAML config）",
        "[x] 特殊字符标签已加引号",
        "[x] 样式已解耦为 classDef",
        "[x] 物理分层清晰",
    ]


def device_label(model: str, role: str, key_param: str) -> str:
    safe_model = model.replace('"', "'")
    return f"{safe_model}\\n{role}\\n({key_param})"


def render_class_defs() -> str:
    lines = ["    %% classDef 节点样式（V4.0）──"]
    for name, spec in NODE_CLASS_DEFS.items():
        lines.append(f"    classDef {name} {spec};")
    return "\n".join(lines)


def render_class_assignments(assignments: dict[str, str]) -> str:
    lines = ["    %% ── class 绑定 ──"]
    for node_id, class_name in assignments.items():
        lines.append(f"    class {node_id} {class_name};")
    return "\n".join(lines)


def layer_subgraph_style(layer_key: str) -> str:
    spec = LAYER_COLORS.get(layer_key, LAYER_COLORS["compute"])
    return (
        f"fill:{spec['fill']},stroke:{spec['stroke']},"
        f"stroke-width:2px,stroke-dasharray:5 5"
    )


def design_note_box(principles: list[str]) -> str:
    lines = "\\n".join(f"{i + 1}. {p}" for i, p in enumerate(principles[:3]))
    return f'    AIDC_NOTE["设计原则\\n{lines}"]'


def minimal_runnable_template() -> str:
    """V4.0 最小可运行基准模板 — 可在 mermaid.live 一次渲染成功."""
    init = aidc_init_directive()
    return f"""{init}
%% AIDC V4.0 最小可运行基准模板 — Spine/Leaf/Compute 三层验证
flowchart TD
    subgraph SPINE ["Spine 汇聚层 (400G)"]
        direction TB
        SPINE_MAIN["NVIDIA Spectrum-4 SN5600\\nSpine 汇聚交换机\\n(64x400G)"]
    end

    subgraph LEAF ["Leaf 接入层 (100G)"]
        direction TB
        LEAF_MAIN["NVIDIA Quantum-2 QM9700\\nLeaf 接入交换机\\n(64x400G IB)"]
    end

    subgraph COMPUTE ["AI 计算集群"]
        direction TB
        GPU_MAIN["8-GPU Training Server\\nAI 训练服务器\\n(8x GPU)"]
    end

    SPINE_MAIN ==>|"400G SR4"| LEAF_MAIN
    LEAF_MAIN -->|"100G DAC"| GPU_MAIN

    classDef spineStyle fill:#E6FFFB,stroke:#13c2c2,stroke-width:2px;
    classDef leafStyle fill:#F6FFED,stroke:#52c41a,stroke-width:2px;
    classDef computeStyle fill:#E6F7FF,stroke:#1890ff,stroke-width:2px;

    class SPINE_MAIN spineStyle;
    class LEAF_MAIN leafStyle;
    class GPU_MAIN computeStyle;
"""


def _unquoted_edge_labels(code: str) -> list[str]:
    labels: list[str] = []
    for m in re.finditer(r"(?:-->|==>|-.->)\|([^|]+)\|", code):
        lbl = m.group(1).strip()
        if not (lbl.startswith('"') and lbl.endswith('"')):
            labels.append(lbl)
    return labels


def _diagram_body(code: str) -> str:
    clean = sanitize_mermaid_for_render(code)
    if "---" in clean:
        return clean.split("---", 2)[-1]
    m = re.search(r"%%\{init:.*?\}%%\s*", clean, re.DOTALL)
    return clean[m.end() :] if m else clean


def validate_mermaid_syntax(code: str) -> list[Violation]:
    """V4.0 语法级校验 — 确保 mermaid.live 可渲染."""
    violations: list[Violation] = []
    clean = sanitize_mermaid_for_render(code)
    if re.search(r"^---\s*\nconfig:", clean, re.M):
        violations.append(
            Violation(
                "config_format",
                "禁止使用 YAML config 块（部分渲染器会 JSON.parse 报错）",
                '%%{init: {"theme":"base",...}}%%',
            )
        )
    if not extract_init_directive(clean) and "themeVariables" not in clean:
        violations.append(
            Violation(
                "config_format",
                "缺少 JSON init 指令",
                '%%{init: {"theme":"base","themeVariables":{"primaryColor":"#1890ff"}}}%%',
            )
        )
    body = _diagram_body(code)
    if not re.search(r"flowchart\s+TD", body, re.I):
        violations.append(Violation("vertical_flow", "缺少 flowchart TD", "flowchart TD"))
    for bad in _unquoted_edge_labels(code):
        violations.append(
            Violation(
                "edge_label_escape",
                f"连线标签未加双引号: {bad}",
                f'-->|"{bad}"|',
            )
        )
    for forbidden in FORBIDDEN_CONFIG_KEYS:
        if forbidden.lower() in code.lower():
            violations.append(
                Violation("mermaid_syntax", f"禁止 config 字段: {forbidden}", "精简 YAML 头")
            )
    if re.search(r"linkStyle\s+\d+", code, re.I):
        violations.append(
            Violation("mermaid_syntax", "禁止 linkStyle 数字索引", "使用 classDef")
        )
    if "classDef" not in code:
        violations.append(Violation("mermaid_syntax", "缺少 classDef", "classDef spineStyle ..."))
    if "themeVariables" not in code:
        violations.append(Violation("mermaid_syntax", "缺少 themeVariables", "primaryColor"))
    return violations


def validate_aidc_compliance(code: str) -> list[Violation]:
    """V4.0 合规校验 — mermaid.live 零报错约束."""
    violations: list[Violation] = []
    upper = code.upper()
    violations.extend(validate_mermaid_syntax(code))

    if "class " not in code and ":::" not in code:
        violations.append(
            Violation(
                "link_semantics",
                "缺少 class 样式绑定",
                "class CORE_SW dataPlane;",
            )
        )

    subgraph_dirs = len(re.findall(r"direction\s+TB", code, re.I))
    subgraph_count = len(re.findall(r"subgraph\s+", code, re.I))
    if subgraph_count > 0 and subgraph_dirs < subgraph_count:
        violations.append(
            Violation(
                "subgraph_layout",
                "subgraph 内缺少 direction TB",
                "subgraph X ... direction TB",
            )
        )

    if subgraph_count < 3:
        violations.append(
            Violation(
                "layer_isolation",
                f"subgraph 分层不足（{subgraph_count}，需≥3）",
                'subgraph COMPUTE["计算层"]',
            )
        )

    for layer in ("COMPUTE", "SPINE", "LEAF"):
        if layer not in upper:
            violations.append(
                Violation("layer_isolation", f"缺少 {layer} 层", f"subgraph {layer}")
            )

    if "AIDC_NOTE" not in code and "设计原则" not in code:
        violations.append(
            Violation(
                "design_principles",
                "缺少设计原则注释框",
                design_note_box(["Spine 不直连服务器"]),
            )
        )

    node_labels: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("subgraph")
            or "-->" in stripped
            or "-.->" in stripped
            or "==>" in stripped
            or stripped.startswith("classDef")
            or stripped.startswith("class ")
            or stripped.startswith("style ")
        ):
            continue
        m = re.search(r'\w+\["([^"]+)"\]', stripped)
        if m:
            node_labels.append(m.group(1))

    bad_labels = [
        lb for lb in node_labels if lb.count("\\n") < 2 and "设计原则" not in lb
    ]
    if bad_labels:
        violations.append(
            Violation(
                "device_identity",
                "设备节点须三行 label（型号/功能/参数）",
                device_label("Model", "功能定位", "关键参数"),
            )
        )

    return violations


def violations_to_dict(items: list[Violation]) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": v.rule_id,
            "message": v.message,
            "fix_snippet": v.fix_snippet,
            "severity": "error",
        }
        for v in items
    ]
