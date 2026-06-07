"""AI-assisted SKU discovery from requirements with optional web snippets."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.exceptions import ValidationError
from app.models.hardware import SKUCategory
from app.repositories.sku_repository import SKURepository
from app.schemas.hardware import SKUCatalogCreate, SKUCatalogRead
from app.schemas.settings import ConsultationProvider
from app.services.consultation_config import (
    parse_llm_json_reply,
    post_llm_chat_completion,
)


async def fetch_web_snippets(query: str, limit: int = 5) -> list[str]:
    """Best-effort web search snippets via DuckDuckGo HTML (no API key)."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    snippets: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; AIDC-CostPro/1.0; +https://example.com/bot)"
                    )
                },
            )
        if response.status_code >= 400:
            return snippets
        text = response.text
        for match in re.finditer(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>',
            text,
            re.IGNORECASE | re.DOTALL,
        ):
            raw = re.sub(r"<[^>]+>", " ", match.group(1))
            cleaned = re.sub(r"\s+", " ", raw).strip()
            if cleaned and len(cleaned) > 20:
                snippets.append(cleaned[:280])
            if len(snippets) >= limit:
                break
    except Exception:
        return snippets
    return snippets


def _pick_gpu(extracted: dict[str, Any], requirement: str) -> tuple[str, str]:
    scenario = str(extracted.get("scenario") or "MIXED")
    gpus = int(extracted.get("target_gpus") or 64)
    text = f"{requirement} {extracted.get('industry', '')}".lower()
    if "ascend" in text or "昇腾" in text or "华为" in text:
        return "Huawei", "Ascend 910B" if gpus < 128 else "Ascend 910C"
    if "amd" in text or "mi300" in text:
        return "AMD", "Instinct MI325X 256G" if gpus >= 128 else "Instinct MI300X 192G"
    if gpus >= 256:
        return "NVIDIA", "B200 SXM 192G"
    if gpus >= 128:
        return "NVIDIA", "H200 SXM 141G"
    if scenario == "INFERENCE":
        return "NVIDIA", "L40S 48G"
    return "NVIDIA", "H800 80G"


def _pick_leaf_switch(switch_ports: int) -> tuple[str, str]:
    if switch_ports >= 64:
        return "Mellanox", "QM9700 Leaf"
    if switch_ports >= 32:
        return "NVIDIA", "Spectrum-3 SN4700 32-port"
    return "NVIDIA", "Spectrum-2 SN4600C 64-port"


def _rule_based_skus(requirement: str, extracted: dict[str, Any] | None) -> list[dict]:
    extracted = extracted or {}
    switch_ports = int(extracted.get("switch_ports") or 32)
    gpu_vendor, gpu_model = _pick_gpu(extracted, requirement)
    leaf_vendor, leaf_model = _pick_leaf_switch(switch_ports)

    return [
        {
            "category": "GPU",
            "vendor": gpu_vendor,
            "model": gpu_model,
            "specs_json": {},
            "base_price": "0",
            "cost_dimension": "COMPUTE",
            "rationale": "匹配算力规模与场景的主流 GPU（预置库）",
        },
        {
            "category": "SWITCH",
            "vendor": leaf_vendor,
            "model": leaf_model,
            "specs_json": {"ports": switch_ports},
            "base_price": "0",
            "cost_dimension": "NETWORK",
            "rationale": "Fat-Tree Leaf 交换机（预置库）",
        },
        {
            "category": "SWITCH",
            "vendor": "Mellanox",
            "model": "QM9700 Spine",
            "specs_json": {"ports": 64},
            "base_price": "0",
            "cost_dimension": "NETWORK",
            "rationale": "Spine 层交换机（预置库）",
        },
        {
            "category": "OPTIC",
            "vendor": "Mellanox",
            "model": "400G-SR8",
            "specs_json": {},
            "base_price": "0",
            "cost_dimension": "NETWORK",
            "rationale": "400G 光模块（预置库）",
        },
        {
            "category": "STORAGE",
            "vendor": "Huawei",
            "model": "OceanStor",
            "specs_json": {},
            "base_price": "0",
            "cost_dimension": "STORAGE",
            "rationale": "并行存储节点（预置库）",
        },
        {
            "category": "SOFTWARE",
            "vendor": "AIDC",
            "model": "Basic_Scheduler",
            "specs_json": {},
            "base_price": "0",
            "cost_dimension": "SOFTWARE",
            "rationale": "基础调度软件（预置库）",
        },
    ]


def _sku_read_to_suggestion(sku: SKUCatalogRead, rationale: str) -> dict[str, Any]:
    return {
        "category": sku.category.value if hasattr(sku.category, "value") else sku.category,
        "vendor": sku.vendor,
        "model": sku.model,
        "specs_json": sku.specs_json,
        "base_price": str(sku.base_price),
        "channel_price": str(sku.channel_price) if sku.channel_price is not None else None,
        "cost_dimension": sku.cost_dimension.value
        if hasattr(sku.cost_dimension, "value")
        else sku.cost_dimension,
        "rationale": rationale,
    }


def _normalize_sku_item(raw: dict[str, Any]) -> SKUCatalogCreate | None:
    try:
        category = SKUCategory(str(raw["category"]).upper())
        cost_dim = raw.get("cost_dimension") or {
            SKUCategory.GPU: "COMPUTE",
            SKUCategory.SWITCH: "NETWORK",
            SKUCategory.OPTIC: "NETWORK",
            SKUCategory.STORAGE: "STORAGE",
            SKUCategory.SOFTWARE: "SOFTWARE",
        }.get(category, "INFRA")
        return SKUCatalogCreate(
            category=category,
            vendor=str(raw.get("vendor") or "Unknown")[:128],
            model=str(raw.get("model") or "Unknown")[:256],
            specs_json=raw.get("specs_json") or {},
            base_price=Decimal(str(raw.get("base_price") or "0")),
            channel_price=(
                Decimal(str(raw["channel_price"])) if raw.get("channel_price") else None
            ),
            cost_dimension=cost_dim,
        )
    except (KeyError, ValueError, ArithmeticError):
        return None


class SkuAiSearchService:
    def __init__(self, sku_repo: SKURepository) -> None:
        self.sku_repo = sku_repo

    async def _resolve_from_catalog(
        self, requirement: str, extracted: dict[str, Any] | None
    ) -> tuple[list[dict[str, Any]], int]:
        """Map rule picks to existing catalog rows when available."""
        picks = _rule_based_skus(requirement, extracted)
        resolved: list[dict[str, Any]] = []
        hits = 0
        for pick in picks:
            category = SKUCategory(str(pick["category"]).upper())
            existing = await self.sku_repo.find_by_identity(
                category, str(pick["vendor"]), str(pick["model"])
            )
            if existing:
                hits += 1
                resolved.append(
                    _sku_read_to_suggestion(
                        SKUCatalogRead.model_validate(existing),
                        str(pick.get("rationale") or "预置 SKU 库"),
                    )
                )
            else:
                resolved.append(pick)
        return resolved, hits

    async def suggest(
        self,
        requirement: str,
        *,
        extracted: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str, str]:
        """Return suggested SKU dicts, summary note, and engine used."""
        settings = settings or {}

        catalog_items, catalog_hits = await self._resolve_from_catalog(requirement, extracted)
        if catalog_hits >= len(catalog_items):
            return (
                catalog_items,
                f"已匹配预置 SKU 库 {catalog_hits} 条（无需网络检索）",
                "catalog",
            )

        provider = settings.get("provider", ConsultationProvider.RULE.value)
        api_key = settings.get("api_key", "")

        if provider == ConsultationProvider.OPENAI_COMPATIBLE.value and api_key:
            web_query = requirement[:200]
            if extracted:
                web_query = (
                    f"{extracted.get('industry', '')} "
                    f"{extracted.get('scenario', '')} GPU datacenter SKU "
                    f"{extracted.get('target_gpus', '')} "
                    f"{requirement[:120]}"
                )
            snippets = await fetch_web_snippets(web_query.strip())
            web_context = (
                "\n".join(f"- {s}" for s in snippets)
                if snippets
                else "（无网络检索结果，使用模型知识）"
            )
            try:
                items = await self._suggest_with_llm(
                    requirement, extracted, web_context, settings
                )
                return items, f"LLM 结合网络检索生成 {len(items)} 条 SKU 建议", "llm"
            except Exception as exc:
                return (
                    catalog_items,
                    f"LLM 失败({exc})，已使用预置库匹配 {catalog_hits} 条",
                    "catalog",
                )

        note = f"预置 SKU 库匹配 {catalog_hits}/{len(catalog_items)} 条"
        return catalog_items, note, "catalog"

    async def _suggest_with_llm(
        self,
        requirement: str,
        extracted: dict[str, Any] | None,
        web_context: str,
        settings: dict[str, Any],
    ) -> list[dict[str, Any]]:
        prompt = (
            "你是数据中心硬件采购顾问。根据需求与网络检索摘要，推荐可写入 SKU 库的产品条目。"
            "返回 JSON：{\"summary\":\"一句话说明\",\"items\":[{\"category\":\"GPU|SWITCH|OPTIC|STORAGE|SOFTWARE\","
            "\"vendor\":\"厂商\",\"model\":\"型号\",\"specs_json\":{},\"base_price\":\"数字字符串\","
            "\"channel_price\":\"可选\",\"cost_dimension\":\"COMPUTE|NETWORK|STORAGE|SOFTWARE\","
            "\"rationale\":\"选用理由\"}]}"
            "至少包含 GPU、Leaf 交换机、Spine 交换机、光模块、存储、调度软件各 1 条。"
        )
        user_content = (
            f"需求：{requirement}\n"
            f"结构化参数：{json.dumps(extracted or {}, ensure_ascii=False)}\n"
            f"网络检索摘要：\n{web_context}"
        )
        response = await post_llm_chat_completion(
            api_base_url=settings["api_base_url"],
            api_key=settings["api_key"],
            model=settings["model"],
            timeout_seconds=settings.get("timeout_seconds", 60),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
        )
        if response.status_code >= 400:
            raise ValidationError(response.text[:200])
        content = response.json()["choices"][0]["message"]["content"]
        parsed = parse_llm_json_reply(content) or {}
        items = parsed.get("items") or []
        if not items:
            raise ValidationError("LLM 未返回 SKU 列表")
        return items

    async def suggest_and_import(
        self,
        requirement: str,
        *,
        extracted: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> tuple[list[SKUCatalogRead], list[SKUCatalogRead], str, list[dict[str, Any]], str]:
        """Suggest SKUs and import ones not already in catalog."""
        raw_items, note, engine = await self.suggest(
            requirement, extracted=extracted, settings=settings
        )
        imported: list[SKUCatalogRead] = []
        skipped: list[SKUCatalogRead] = []

        for raw in raw_items:
            payload = _normalize_sku_item(raw)
            if payload is None:
                continue
            existing = await self.sku_repo.find_by_identity(
                payload.category, payload.vendor, payload.model
            )
            if existing:
                skipped.append(SKUCatalogRead.model_validate(existing))
                continue
            created = await self.sku_repo.create(payload)
            imported.append(SKUCatalogRead.model_validate(created))

        summary = f"{note}；新增 {len(imported)} 条，已有 {len(skipped)} 条"
        return imported, skipped, summary, raw_items, engine
