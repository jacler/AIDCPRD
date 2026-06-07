"""AIDC V4.0 architecture diagram engine — acceptance tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.export.delivery_package import build_delivery_package, generate_delivery_package
from app.templates.arch_patterns import auto_select_template, match_pattern
from app.visualizer.aidc_golden_rules import (
    minimal_runnable_template,
    sanitize_mermaid_for_render,
    upgrade_legacy_mermaid,
    validate_aidc_compliance,
    validate_mermaid_syntax,
)
from app.export.diagram_exporter import export_diagram
from app.visualizer.diagram_generator import generate_architecture_diagram
from app.visualizer.public_models import resolve_model

FIXTURES = Path(__file__).parent / "fixtures" / "complex_scenarios.json"


def test_auto_select_2048_pretrain():
    assert auto_select_template({"requirement": "2048卡预训练", "target_gpus": 2048}) == "rail_optimized"


def test_auto_select_enterprise_sft():
    assert auto_select_template({"requirement": "企业级SFT微调", "target_gpus": 64}) == "fat_tree_inference"


def test_match_wan_ka_training():
    p = match_pattern("万卡训练大模型预训练", target_gpus=1024)
    assert p.pattern_id == "rail_optimized"


def test_match_enterprise_inference():
    p = match_pattern("企业级推理服务", target_gpus=32, scenario="INFERENCE")
    assert p.pattern_id == "fat_tree_inference"


def test_internal_model_replacement():
    r = resolve_model("R5500 G6")
    assert r.is_public_equivalent
    assert any("等效" in w or "替换" in w for w in r.warnings)
    assert "Public Equivalent" in r.label or "8-GPU" in r.model


def test_minimal_runnable_template_v40():
    code = minimal_runnable_template()
    assert not re.search(r"linkStyle\s+\d+", code)
    assert "rankSpacing" not in code
    assert "classDef" in code
    assert "direction TB" in code
    assert code.strip().startswith("%%{init:")
    assert "config:" not in code.split("flowchart")[0]
    assert re.search(r'==>\|"400G SR4"\|', code)
    assert not validate_mermaid_syntax(code)


LEGACY_MERMAID_SNIPPET = """%% WEB_INTERACTIVE pattern=rail_optimized convergence=1:1
%% click TRAIN "训练区详情" _blank
---
config:
  theme: base
  securityLevel: loose
  themeVariables:
    primaryColor: '#1890ff'
    fontSize: '14px'
    fontFamily: 'Microsoft YaHei'
---
flowchart TD
    SPINE_MAIN ==>|400G · 1:1| LEAF_MAIN
    GPU_R1 -->|DAC/400G| LEAF_MAIN
"""


def test_upgrade_legacy_v3_mermaid_to_v4():
    upgraded = sanitize_mermaid_for_render(upgrade_legacy_mermaid(LEGACY_MERMAID_SNIPPET))
    assert upgraded.strip().startswith("%%{init:")
    assert "WEB_INTERACTIVE" not in upgraded
    assert "config:" not in upgraded.split("flowchart")[0]
    assert '|"400G · 1:1"|' in upgraded
    syntax_issues = [v.rule_id for v in validate_mermaid_syntax(upgraded)]
    assert "config_format" not in syntax_issues
    assert "yaml_purity" not in syntax_issues
    assert "edge_label_escape" not in syntax_issues


def test_web_export_must_start_with_init_directive():
    result = generate_architecture_diagram(requirement="万卡训练", target_gpus=1024)
    bundle = export_diagram(result, "web_interactive")
    assert bundle.mermaid_code.strip().startswith("%%{init:")
    assert "%% WEB_INTERACTIVE" not in bundle.mermaid_code


def test_aidc_golden_rules_compliance():
    result = generate_architecture_diagram(requirement="万卡训练", target_gpus=1024)
    violations = validate_aidc_compliance(result.mermaid_code)
    assert not violations, violations
    assert "flowchart TD" in result.mermaid_code
    assert not re.search(r"linkStyle\s+\d+", result.mermaid_code)
    assert "classDef" in result.mermaid_code
    assert "设计原则" in result.mermaid_code
    assert "subgraph CORE" in result.mermaid_code
    assert "direction TB" in result.mermaid_code
    assert result.mermaid_code.strip().startswith("%%{init:")
    assert "[x] 使用 JSON init 指令（非 YAML config）" in result.compliance_checklist


def test_delivery_package_complete():
    pkg = generate_delivery_package(requirement="2048卡预训练", target_gpus=2048, export_mode="ppt_ready")
    assert pkg.mermaid_code
    assert "| 网络层 |" in pkg.param_table
    assert len(pkg.talking_points) <= 3
    assert "不构成商业承诺" in pkg.compliance_statement
    assert pkg.render_guide.get("dpi") == 300


@pytest.mark.parametrize("scenario", json.loads(FIXTURES.read_text(encoding="utf-8"))["scenarios"])
def test_complex_scenarios(scenario: dict):
    expected = scenario["expected_pattern"]
    result = generate_architecture_diagram(
        requirement=scenario["requirement"],
        target_gpus=scenario["target_gpus"],
        scenario=scenario.get("scenario", "TRAINING"),
        liquid_cooling=scenario.get("liquid_cooling", False),
        domestic_mode=scenario.get("domestic_mode", False),
        device_overrides=scenario.get("device_overrides"),
    )
    assert result.pattern_id == expected
    assert not validate_aidc_compliance(result.mermaid_code)

    if scenario.get("domestic_mode"):
        assert "Ascend" in result.mermaid_code

    if scenario["id"] == "poc_8gpu":
        assert result.pattern_id == "fat_tree_inference"


@pytest.mark.asyncio
async def test_diagram_api_generate(client: AsyncClient, auth_headers: dict):
    res = await client.post(
        "/api/v1/diagrams/generate",
        json={"requirement": "2048卡预训练", "target_gpus": 2048, "export_mode": "ppt_ready"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["pattern_id"] == "rail_optimized"
    assert "flowchart TD" in data["mermaid_code"]
    assert data["param_table"]
    assert data["compliance_checklist"]


@pytest.mark.asyncio
async def test_diagram_api_project(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "V3Diagram", "target_gpus": 64, "scenario": "TRAINING"},
        headers=auth_headers,
    )
    pid = create.json()["id"]
    await client.post(
        "/api/v1/projects/generate-topology",
        json={"target_gpus": 64, "scenario": "TRAINING", "project_id": pid},
        headers=auth_headers,
    )
    res = await client.post(
        f"/api/v1/diagrams/projects/{pid}/generate",
        json={"export_mode": "ppt_ready"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["export_mode"] == "ppt_ready"
    assert not validate_aidc_compliance(body["mermaid_code"])
