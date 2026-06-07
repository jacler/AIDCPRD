"""Smoke test all V2 API endpoints against a running server."""

from __future__ import annotations

import asyncio
import sys

import httpx

BASE = "http://localhost:8000"
EMAIL = "admin@example.com"
PASSWORD = "admin123"

ENDPOINTS: list[tuple[str, str, dict | None]] = [
    ("GET", "/health", None),
    ("GET", "/api/v1/settings/consultation/prompt-presets", None),
    ("GET", "/api/v1/settings/consultation", None),
    ("GET", "/api/v1/projects?page=1&page_size=5", None),
    ("GET", "/api/v1/catalog/categories", None),
    ("GET", "/api/v1/catalog/skus?page=1&page_size=5", None),
]


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE, timeout=30.0, trust_env=False) as client:
        for method, path, body in ENDPOINTS:
            r = await client.request(method, path, json=body)
            if r.status_code == 404:
                print(f"FAIL 404 {method} {path}")
                return 1
            print(f"OK   {r.status_code} {method} {path}")

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"FAIL login {login.status_code}: {login.text}")
            return 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        auth_checks = [
            ("POST", "/api/v1/consultation/chat", {"message": "想训个大模型", "history": []}),
            ("POST", "/api/v1/projects", {"name": "SmokeTest", "target_gpus": 64, "scenario": "TRAINING"}),
        ]
        project_id = None
        for method, path, body in auth_checks:
            r = await client.request(method, path, json=body, headers=headers)
            if r.status_code == 404:
                print(f"FAIL 404 {method} {path}")
                return 1
            if path == "/api/v1/projects" and r.status_code == 201:
                project_id = r.json()["id"]
            print(f"OK   {r.status_code} {method} {path}")

        assert project_id
        topo = await client.post(
            "/api/v1/projects/generate-topology",
            json={"target_gpus": 64, "scenario": "TRAINING", "project_id": project_id},
            headers=headers,
        )
        print(f"OK   {topo.status_code} POST /api/v1/projects/generate-topology")

        protected = [
            ("GET", f"/api/v1/projects/{project_id}", None),
            ("GET", f"/api/v1/projects/{project_id}/multi-plan", None),
            ("GET", f"/api/v1/export/projects/{project_id}/visualizations", None),
            ("GET", f"/api/v1/export/projects/{project_id}/technical-proposal", None),
            (
                "POST",
                f"/api/v1/compliance/projects/{project_id}/evaluate",
                {"domestic_mode": False, "frameworks": ["pytorch"]},
            ),
            ("GET", f"/api/v1/compliance/projects/{project_id}/appendix", None),
        ]
        for method, path, body in protected:
            r = await client.request(method, path, json=body, headers=headers)
            if r.status_code == 404:
                print(f"FAIL 404 {method} {path} -> {r.text[:200]}")
                return 1
            print(f"OK   {r.status_code} {method} {path}")

        await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
        print("Smoke test passed.")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
