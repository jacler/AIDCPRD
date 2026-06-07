import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_and_me(client: AsyncClient, auth_headers: dict):
    me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "admin@example.com"
    assert data["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_auth_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "display_name": "普通用户",
            "password": "user1234",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "USER"


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/catalog/skus")
    assert response.status_code == 401
