import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_generate_topology_512(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/projects/generate-topology",
        json={
            "target_gpus": 512,
            "scenario": "TRAINING",
            "network_arch": "FAT_TREE",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["compute"]["servers"] == 64
    assert data["compute"]["gpus"] == 512
    assert data["network"]["leaf_switches"] == 16
    assert data["network"]["spine_switches"] == 8
    assert data["storage"]["nodes"] == 8
    assert len(data["bom"]) == 6


@pytest.mark.asyncio
async def test_sku_catalog_crud(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/v1/catalog/skus",
        json={
            "category": "GPU",
            "vendor": "NVIDIA",
            "model": "A100",
            "specs_json": {"memory_gb": 80},
            "base_price": "100000.00",
            "cost_dimension": "COMPUTE",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    sku_id = create_resp.json()["id"]

    list_resp = await client.get(
        "/api/v1/catalog/skus", params={"category": "GPU"}, headers=auth_headers
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    get_resp = await client.get(f"/api/v1/catalog/skus/{sku_id}", headers=auth_headers)
    assert get_resp.status_code == 200

    update_resp = await client.put(
        f"/api/v1/catalog/skus/{sku_id}",
        json={"channel_price": "95000.00"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["channel_price"] == "95000.00"

    delete_resp = await client.delete(f"/api/v1/catalog/skus/{sku_id}", headers=auth_headers)
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_project_lifecycle_and_cost(client: AsyncClient, seed_skus, auth_headers: dict):
    skus = seed_skus

    project_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "512卡训练集群",
            "target_gpus": 512,
            "scenario": "TRAINING",
        },
        headers=auth_headers,
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    topo_resp = await client.post(
        "/api/v1/projects/generate-topology",
        json={
            "target_gpus": 512,
            "scenario": "TRAINING",
            "network_arch": "FAT_TREE",
            "project_id": project_id,
        },
        headers=auth_headers,
    )
    assert topo_resp.status_code == 200

    gpu_sku = next(s for s in skus if s["category"] == "GPU")
    switch_skus = [s for s in skus if s["category"] == "SWITCH"]
    optic_sku = next(s for s in skus if s["category"] == "OPTIC")
    storage_sku = next(s for s in skus if s["category"] == "STORAGE")
    software_sku = next(s for s in skus if s["category"] == "SOFTWARE")

    cost_resp = await client.post(
        f"/api/v1/projects/{project_id}/calculate-cost",
        json={
            "bom_items": [
                {"sku_id": gpu_sku["id"], "quantity": 512},
                {"sku_id": switch_skus[0]["id"], "quantity": 16},
                {"sku_id": switch_skus[1]["id"], "quantity": 8},
                {"sku_id": optic_sku["id"], "quantity": 1024},
                {"sku_id": storage_sku["id"], "quantity": 8},
                {"sku_id": software_sku["id"], "quantity": 1},
            ],
            "pricing_rules": {"free_scheduler_with_server": True},
        },
        headers=auth_headers,
    )
    assert cost_resp.status_code == 200
    data = cost_resp.json()
    assert data["cost_breakdown"]["SOFTWARE"] == 0.0
    assert data["cost_breakdown"]["total"] > 0
    assert len(data["bom"]) == 6

    detail_resp = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == "COMPLETED"
