"""Phase 4 acceptance — topology SVG, cabinet layout, Word export."""

import io
import zipfile

import pytest
from httpx import AsyncClient

from app.export.doc_generator import DISCLAIMER_FOOTER, TechnicalProposalInput, generate_technical_proposal_docx
from app.visualizer.cabinet_layout import plan_rack_layout, render_cabinet_layout_svg
from app.visualizer.topology_renderer import compute_convergence_ratio, render_topology_svgs


SAMPLE_TOPOLOGY = {
    "compute": {"servers": 32, "gpus": 256},
    "network": {
        "leaf_switches": 8,
        "spine_switches": 4,
        "rdma_nics": 256,
        "dac_cables": 256,
        "optics_400g": 64,
    },
    "storage": {"nodes": 6},
}


def test_topology_svg_separates_compute_and_storage():
    result = render_topology_svgs(SAMPLE_TOPOLOGY)
    assert "<svg" in result.compute_svg
    assert "<svg" in result.storage_svg
    assert "计算网" in result.compute_svg
    assert "存储网" in result.storage_svg
    assert "SR4" in result.compute_svg or "LR4" in result.compute_svg
    assert "DAC" in result.compute_svg
    assert result.convergence_ratio


def test_convergence_ratio_nonblocking():
    ratio = compute_convergence_ratio(servers=16, gpus_per_node=8, leaf_switches=4, switch_ports=64)
    assert ratio == "1:1"


def test_cabinet_layout_respects_power_limit():
    layout = plan_rack_layout(server_count=20, gpus_per_node=8, gpu_tdp_w=700)
    assert layout.total_racks >= 1
    assert "PDU" in layout.svg
    assert layout.power_limit_kw_per_rack == 15.0
    for rack in layout.racks:
        assert rack.total_u <= 42 + 4


def test_cabinet_svg_from_topology():
    layout = render_cabinet_layout_svg(SAMPLE_TOPOLOGY)
    assert layout.total_racks >= 2
    assert "机柜排布" in layout.svg


def test_word_export_has_sections_and_disclaimer():
    payload = TechnicalProposalInput(
        project_name="测试集群",
        target_gpus=256,
        scenario="TRAINING",
        description="等保三级训练集群",
        topology=SAMPLE_TOPOLOGY,
        cost_breakdown={"COMPUTE": 1, "NETWORK": 1, "STORAGE": 1, "SOFTWARE": 1, "INFRA": 1, "total": 5},
        bom_items=[
            {
                "category": "GPU",
                "model": "H100 SXM",
                "quantity": 256,
                "unit_price": 200000,
                "total_price": 51200000,
                "cost_dimension": "COMPUTE",
            }
        ],
        multi_plans=[
            {
                "plan_id": "balanced",
                "headline": "均衡方案",
                "convergence_ratio": "1:1",
                "tco_5y": 50_000_000,
                "trade_offs": ["折中方案"],
            }
        ],
        compliance_result={
            "security_checklist": [
                {
                    "title": "边界防护",
                    "status": "warn",
                    "status_icon": "⚠️",
                    "remediation": "部署防火墙",
                    "regulation_ref": "GB/T 22239-2019",
                }
            ],
            "appendix_markdown": "## 合规附录\n测试",
        },
        topology_compute_svg=render_topology_svgs(SAMPLE_TOPOLOGY).compute_svg,
        topology_storage_svg=render_topology_svgs(SAMPLE_TOPOLOGY).storage_svg,
        cabinet_svg=render_cabinet_layout_svg(SAMPLE_TOPOLOGY).svg,
        convergence_ratio="1:1",
        consultation_summary=["确认训练规模为 256 GPU", "采用模型并行策略"],
    )
    raw = generate_technical_proposal_docx(payload)
    assert len(raw) > 5000
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        footer_xml = zf.read("word/footer1.xml").decode("utf-8")
    for keyword in ("项目背景", "需求诊断", "拓扑设计", "方案权衡", "BOM", "合规自查", "数据来源"):
        assert keyword in doc_xml
    assert DISCLAIMER_FOOTER in footer_xml


@pytest.mark.asyncio
async def test_export_api_visualizations(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "Phase4 Viz", "target_gpus": 64, "scenario": "TRAINING"},
        headers=auth_headers,
    )
    project_id = create.json()["id"]
    await client.post(
        "/api/v1/projects/generate-topology",
        json={
            "target_gpus": 64,
            "scenario": "TRAINING",
            "project_id": project_id,
        },
        headers=auth_headers,
    )
    res = await client.get(
        f"/api/v1/export/projects/{project_id}/visualizations",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "compute_network_svg" in data
    assert "storage_network_svg" in data
    assert data["convergence_ratio"]


@pytest.mark.asyncio
async def test_export_api_technical_proposal_docx(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "Phase4 Doc", "target_gpus": 32, "scenario": "TRAINING"},
        headers=auth_headers,
    )
    project_id = create.json()["id"]
    await client.post(
        "/api/v1/projects/generate-topology",
        json={
            "target_gpus": 32,
            "scenario": "TRAINING",
            "project_id": project_id,
        },
        headers=auth_headers,
    )
    res = await client.get(
        f"/api/v1/export/projects/{project_id}/technical-proposal",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert "wordprocessingml" in res.headers.get("content-type", "")
    assert len(res.content) > 3000


@pytest.mark.asyncio
async def test_export_chinese_project_name_filename(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "智算训练集群", "target_gpus": 16, "scenario": "TRAINING"},
        headers=auth_headers,
    )
    project_id = create.json()["id"]
    await client.post(
        "/api/v1/projects/generate-topology",
        json={"target_gpus": 16, "scenario": "TRAINING", "project_id": project_id},
        headers=auth_headers,
    )
    res = await client.get(
        f"/api/v1/export/projects/{project_id}/technical-proposal",
        headers=auth_headers,
    )
    assert res.status_code == 200
    disposition = res.headers.get("content-disposition", "")
    assert "filename*=" in disposition
