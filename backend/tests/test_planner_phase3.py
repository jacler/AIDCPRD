"""Phase 3 acceptance — compliance adapter, checklist, audit."""

import pytest
from httpx import AsyncClient

from app.compliance.domestic_adapter import adapt_catalog_items, check_framework_compatibility
from app.compliance.security_checklist import CheckStatus, generate_security_checklist
from app.compliance.service import ComplianceService


def test_ascend_pytorch_shows_compatibility_gap():
    gap = check_framework_compatibility("pytorch", "Ascend")
    assert gap is not None
    assert gap.status == "partial"
    assert gap.compatibility_gap
    assert gap.remediation


def test_domestic_mode_tensorflow_on_ascend():
    result = adapt_catalog_items(
        [{"vendor": "NVIDIA", "model": "H800 80G", "category": "GPU"}],
        domestic_mode=True,
        frameworks=["tensorflow"],
    )
    assert result.enabled
    assert len(result.replacements) == 1
    assert result.replacements[0].domestic_model == "Ascend 910B"
    assert any(g.framework == "tensorflow" for g in result.compatibility_gaps)


def test_security_checklist_level3_cross_domain():
    items = generate_security_checklist(
        {
            "compliance": "等保三级",
            "cross_domain": True,
            "network_zoned": False,
            "target_gpus": 128,
        }
    )
    boundary = next(i for i in items if i.item_id == "boundary_protection")
    assert boundary.status == CheckStatus.FAIL
    assert "GB/T 22239-2019" in boundary.regulation_ref


def test_audit_appendix_generated():
    service = ComplianceService()
    result = service.evaluate(
        project_name="测试集群",
        target_gpus=64,
        compliance="等保三级",
        domestic_mode=True,
        frameworks=["pytorch", "tensorflow"],
        bom_items=[{"vendor": "NVIDIA", "model": "H800 80G", "category": "GPU"}],
    )
    assert result["appendix_markdown"]
    assert "合规判定依据附录" in result["appendix_markdown"]
    assert "免责声明" in result["appendix_markdown"]
    assert len(result["audit_trail"]) >= 3


@pytest.mark.asyncio
async def test_compliance_api_domestic_mode(client: AsyncClient, auth_headers: dict, seed_skus):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "信创测试", "target_gpus": 64, "scenario": "TRAINING"},
        headers=auth_headers,
    )
    project_id = create.json()["id"]

    await client.post(
        "/api/v1/projects/generate-topology",
        json={"target_gpus": 64, "scenario": "TRAINING", "project_id": project_id},
        headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/compliance/projects/{project_id}/evaluate",
        json={"domestic_mode": True, "frameworks": ["tensorflow"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    gaps = data["domestic_adaptation"]["compatibility_gaps"]
    assert any("tensorflow" in g["framework"] for g in gaps)

    appendix = await client.get(
        f"/api/v1/compliance/projects/{project_id}/appendix",
        headers=auth_headers,
    )
    assert appendix.status_code == 200
    assert "合规判定依据附录" in appendix.text
