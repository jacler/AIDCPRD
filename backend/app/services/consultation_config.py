import json
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.exceptions import ValidationError
from app.data.consultation_prompt_presets import (
    CONSULTATION_PROMPT_PRESETS,
    DEFAULT_PRESET_ID,
    PRESET_BY_ID,
)
from app.repositories.app_settings_repository import AppSettingsRepository
from app.schemas.settings import (
    CONSULTATION_SETTINGS_KEY,
    DEFAULT_CONSULTATION_SETTINGS,
    ConsultationProvider,
    ConsultationSettingsRead,
    ConsultationSettingsUpdate,
)


def _mask_api_key(api_key: str) -> bool:
    return bool(api_key and api_key.strip())


def _resolve_preset_id(merged: dict) -> str:
    preset_id = merged.get("system_prompt_preset_id")
    if preset_id:
        return preset_id
    prompt = merged.get("system_prompt", "")
    for preset in CONSULTATION_PROMPT_PRESETS:
        if prompt == preset.prompt:
            return preset.id
    return "custom" if prompt else DEFAULT_PRESET_ID


def _to_read(raw: dict) -> ConsultationSettingsRead:
    merged = {**DEFAULT_CONSULTATION_SETTINGS, **raw}
    return ConsultationSettingsRead(
        enabled=merged["enabled"],
        provider=ConsultationProvider(merged["provider"]),
        api_base_url=merged["api_base_url"],
        api_key_configured=_mask_api_key(merged.get("api_key", "")),
        model=merged["model"],
        timeout_seconds=merged["timeout_seconds"],
        system_prompt_preset_id=_resolve_preset_id(merged),
        system_prompt=merged["system_prompt"],
    )


def normalize_api_key(raw: str) -> str:
    """Strip wrappers and ensure API key is ASCII-safe for HTTP headers."""
    if not raw:
        return ""

    key = raw.strip()
    lowered = key.lower()
    if lowered.startswith("authorization:"):
        key = key.split(":", 1)[1].strip()
        lowered = key.lower()
    if lowered.startswith("bearer "):
        key = key[7:].strip()

    if "：" in key or ":" in key:
        key = re.split(r"[：:]", key)[-1].strip()

    sk_match = re.search(r"(sk-[A-Za-z0-9_-]+)", key)
    if sk_match:
        return sk_match.group(1)

    if not key.isascii():
        tokens = re.findall(r"[A-Za-z0-9_-]{8,}", key)
        if tokens:
            return max(tokens, key=len)
        raise ValidationError(
            "API Key 含有中文或非法字符。请仅粘贴 Key 本身，"
            "不要包含「密钥」「Bearer」等前缀或说明文字。"
        )

    return key


async def post_llm_chat_completion(
    *,
    api_base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: int = 60,
    temperature: float = 0.3,
) -> httpx.Response:
    """Call OpenAI-compatible /chat/completions with UTF-8 body and ASCII headers."""
    normalized_key = normalize_api_key(api_key)
    if not normalized_key:
        raise ValidationError("OpenAI 兼容模式需要配置 API Key")

    base = api_base_url.rstrip("/")
    url = f"{base}/chat/completions"
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": temperature},
        ensure_ascii=False,
    ).encode("utf-8")

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        return await client.post(
            url,
            headers={
                "Authorization": f"Bearer {normalized_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            content=payload,
        )


async def stream_llm_chat_completion(
    *,
    api_base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: int = 60,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    """Stream OpenAI-compatible /chat/completions content deltas."""
    normalized_key = normalize_api_key(api_key)
    if not normalized_key:
        raise ValidationError("OpenAI 兼容模式需要配置 API Key")

    base = api_base_url.rstrip("/")
    url = f"{base}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        async with client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {normalized_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            content=payload,
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", errors="replace")
                raise ValidationError(
                    format_llm_api_error(response.status_code, body, api_base_url)
                )

            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content


class ConsultationConfigService:
    def __init__(self, repo: AppSettingsRepository) -> None:
        self.repo = repo

    async def get_settings(self) -> ConsultationSettingsRead:
        raw = await self.repo.get_value(CONSULTATION_SETTINGS_KEY)
        if raw is None:
            return _to_read(DEFAULT_CONSULTATION_SETTINGS)
        return _to_read(raw)

    async def get_raw_settings(self) -> dict:
        raw = await self.repo.get_value(CONSULTATION_SETTINGS_KEY)
        merged = {**DEFAULT_CONSULTATION_SETTINGS, **(raw or {})}
        api_key = merged.get("api_key", "")
        if api_key:
            merged["api_key"] = normalize_api_key(str(api_key))
        preset_id = _resolve_preset_id(merged)
        merged["system_prompt_preset_id"] = preset_id
        if preset_id != "custom" and preset_id in PRESET_BY_ID:
            merged["system_prompt"] = PRESET_BY_ID[preset_id].prompt
        return merged

    async def update_settings(self, payload: ConsultationSettingsUpdate) -> ConsultationSettingsRead:
        current = await self.get_raw_settings()
        updates = payload.model_dump(exclude_unset=True)

        preset_id = updates.pop("system_prompt_preset_id", None)
        custom_prompt = updates.pop("system_prompt", None)

        if preset_id == "custom":
            current["system_prompt_preset_id"] = "custom"
            if custom_prompt is not None and custom_prompt.strip():
                current["system_prompt"] = custom_prompt.strip()
        elif preset_id and preset_id in PRESET_BY_ID:
            current["system_prompt_preset_id"] = preset_id
            current["system_prompt"] = PRESET_BY_ID[preset_id].prompt
        elif custom_prompt is not None:
            current["system_prompt_preset_id"] = "custom"
            current["system_prompt"] = custom_prompt

        if "api_key" in updates:
            new_key = updates.pop("api_key")
            if new_key is not None and new_key.strip():
                current["api_key"] = normalize_api_key(new_key)
            elif new_key == "":
                current["api_key"] = ""

        for key, value in updates.items():
            if value is not None:
                if key == "provider":
                    current[key] = value.value if hasattr(value, "value") else value
                else:
                    current[key] = value

        await self.repo.upsert(CONSULTATION_SETTINGS_KEY, current)
        return _to_read(current)

    async def test_connection(self, probe_message: str) -> tuple[bool, str, ConsultationProvider]:
        settings = await self.get_raw_settings()
        provider = ConsultationProvider(settings["provider"])

        if not settings.get("enabled", True):
            return False, "智能咨询已禁用，请先在设置中启用", provider

        if provider == ConsultationProvider.RULE:
            return True, "规则引擎模式可用，无需外部 API", provider

        api_key = settings.get("api_key", "")
        if not api_key:
            return False, "OpenAI 兼容模式需要配置 API Key", provider

        timeout = settings.get("timeout_seconds", 60)

        try:
            response = await post_llm_chat_completion(
                api_base_url=settings["api_base_url"],
                api_key=api_key,
                model=settings["model"],
                timeout_seconds=timeout,
                messages=[
                    {"role": "system", "content": settings["system_prompt"]},
                    {"role": "user", "content": probe_message},
                ],
            )
            if response.status_code >= 400:
                return False, format_llm_api_error(
                    response.status_code, response.text, settings["api_base_url"]
                ), provider
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return True, f"连接成功，模型回复：{content[:120]}…", provider
        except ValidationError as exc:
            return False, str(exc.detail), provider
        except Exception as exc:
            return False, f"连接失败：{exc}", provider


def format_llm_api_error(status_code: int, response_text: str, api_base_url: str = "") -> str:
    """Turn raw LLM HTTP errors into actionable Chinese messages."""
    detail = response_text.strip()
    try:
        data = json.loads(response_text)
        err = data.get("error")
        if isinstance(err, dict):
            detail = str(err.get("message") or detail)
        elif isinstance(err, str):
            detail = err
    except json.JSONDecodeError:
        pass

    detail = detail[:300]
    base = api_base_url.lower()

    if status_code == 401:
        hints = ["请确认 API Key 完整无误、未过期，且与下方 API Base URL 来自同一服务商。"]
        if "openai.com" in base:
            hints.append("OpenAI 地址需使用 platform.openai.com 创建的 Key，不能使用 DeepSeek/通义等 Key。")
        elif "deepseek.com" in base:
            hints.append("DeepSeek 地址需使用 platform.deepseek.com 的 Key。")
        elif "dashscope" in base or "aliyuncs" in base:
            hints.append("通义地址需使用阿里云 DashScope 的 API Key。")
        return f"认证失败 (401)：{detail} {' '.join(hints)}"

    if status_code == 404:
        return f"接口不存在 (404)：请检查 API Base URL 是否正确（当前：{api_base_url}）"

    if status_code == 429:
        return f"请求过于频繁 (429)：{detail}"

    return f"API 返回错误 {status_code}：{detail}"


async def seed_consultation_settings(repo: AppSettingsRepository) -> None:
    existing = await repo.get_value(CONSULTATION_SETTINGS_KEY)
    if existing is None:
        await repo.upsert(CONSULTATION_SETTINGS_KEY, DEFAULT_CONSULTATION_SETTINGS.copy())


def parse_llm_json_reply(content: str) -> dict[str, Any] | None:
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def extract_partial_reply(content: str) -> str | None:
    """Extract reply field value from complete or in-progress JSON text."""
    marker = re.search(r'"reply"\s*:\s*"', content)
    if not marker:
        return None

    rest = content[marker.end() :]
    chars: list[str] = []
    i = 0
    while i < len(rest):
        ch = rest[i]
        if ch == "\\" and i + 1 < len(rest):
            nxt = rest[i + 1]
            if nxt == "n":
                chars.append("\n")
            elif nxt == "t":
                chars.append("\t")
            elif nxt == '"':
                chars.append('"')
            elif nxt == "\\":
                chars.append("\\")
            else:
                chars.append(nxt)
            i += 2
            continue
        if ch == '"':
            break
        chars.append(ch)
        i += 1
    return "".join(chars) if chars else None


class ReplyFieldExtractor:
    """Yield only human-readable reply deltas while LLM JSON is streaming."""

    def __init__(self) -> None:
        self._content = ""
        self._emitted_len = 0

    def feed(self, chunk: str) -> str:
        self._content += chunk
        reply = extract_partial_reply(self._content)
        if not reply or len(reply) <= self._emitted_len:
            return ""
        delta = reply[self._emitted_len :]
        self._emitted_len = len(reply)
        return delta
