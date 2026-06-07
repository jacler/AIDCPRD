"""Rule-based and LLM-backed requirement consultation."""

from __future__ import annotations

import json
import math
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import ValidationError
from app.planner.engine import ConsultationPlanner
from app.planner.intent_classifier import Intent
from app.planner.slot_parser import enrich_slots_from_message
from app.schemas.consultation import (
    ConsultationChatResponse,
    ConsultationMessage,
    ExtractedRequirements,
)
from app.schemas.hardware import ProjectScenario
from app.schemas.settings import ConsultationProvider
from app.services.consultation_config import (
    ReplyFieldExtractor,
    format_llm_api_error,
    parse_llm_json_reply,
    post_llm_chat_completion,
    stream_llm_chat_completion,
)

_sessions: dict[str, ConsultationSession] = {}
_planner = ConsultationPlanner()


def _intent_to_scenario(intent_value: str | None) -> ProjectScenario | None:
    if intent_value in (Intent.PRETRAIN.value, Intent.SFT.value, Intent.RLHF.value):
        return ProjectScenario.TRAINING
    if intent_value == Intent.INFERENCE.value:
        return ProjectScenario.INFERENCE
    return None


def _planner_context_lines(slots: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if slots.get("industry") == "healthcare":
        lines.append("已识别为**医疗行业**场景，将优先考虑推理负载、数据合规与存储冗余。")
    elif slots.get("industry"):
        lines.append(f"已识别行业标签：{slots['industry']}。")
    if slots.get("compute_pflops"):
        lines.append(
            f"目标算力约 **{slots['compute_pflops']}P**，"
            f"折算建议 GPU 规模约 **{slots.get('target_gpus', '—')} 张**。"
        )
    elif slots.get("target_gpus"):
        lines.append(f"目标 GPU 数量：**{slots['target_gpus']} 张**。")
    if slots.get("scenario"):
        scenario_cn = {
            ProjectScenario.TRAINING: "训练",
            ProjectScenario.INFERENCE: "推理",
            ProjectScenario.MIXED: "训推混合",
        }
        sc = slots["scenario"]
        if isinstance(sc, ProjectScenario):
            lines.append(f"应用场景：**{scenario_cn.get(sc, sc.value)}**。")
    if slots.get("compliance"):
        lines.append(f"合规要求：{slots['compliance']}。")
    if slots.get("token_scale_monthly"):
        lines.append(f"已记录月 Token 规模：**{slots['token_scale_monthly']}**。")
    if slots.get("parallel_strategy"):
        label = (
            "数据并行"
            if slots["parallel_strategy"] == "data_parallel"
            else "模型/流水线并行"
        )
        lines.append(f"并行策略：**{label}**。")
    if slots.get("inference_qps_peak"):
        lines.append(f"推理峰值 QPS：**{slots['inference_qps_peak']}**。")
    if slots.get("latency_p99_ms"):
        lines.append(f"P99 延迟目标：**{slots['latency_p99_ms']} ms**。")
    return lines


@dataclass
class ConsultationSession:
    session_id: str
    project_id: str | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    messages: list[ConsultationMessage] = field(default_factory=list)
    asked: set[str] = field(default_factory=set)


def _scope_id(project_id: str | None) -> str:
    return str(project_id) if project_id else "draft"


def _session_storage_key(project_id: str | None, session_id: str) -> str:
    return f"{_scope_id(project_id)}:{session_id}"


def _get_or_create_session(
    project_id: str | None,
    session_id: str | None,
) -> tuple[ConsultationSession, str]:
    if session_id:
        key = _session_storage_key(project_id, session_id)
        if key in _sessions:
            return _sessions[key], session_id
    new_session_id = str(uuid.uuid4())
    key = _session_storage_key(project_id, new_session_id)
    session = ConsultationSession(session_id=new_session_id, project_id=project_id)
    _sessions[key] = session
    return session, new_session_id


def _append_user_message(session: ConsultationSession, message: str) -> None:
    session.messages.append(ConsultationMessage(role="user", content=message))
    if not session.slots.get("description"):
        session.slots["description"] = message
    else:
        session.slots["description"] = f"{session.slots['description']}\n{message}"


def _stream_text_chunks(text: str, chunk_size: int = 16) -> list[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [""]


def _parse_pflops(text: str) -> float | None:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*[pP](?:算力|FLOPS|flops)?",
        r"(\d+(?:\.\d+)?)\s*P(?:eta)?",
        r"(\d+(?:\.\d+)?)\s*PFLOPS",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return float(m.group(1))
    return None


def _parse_gpu_count(text: str) -> int | None:
    patterns = [
        r"(\d+)\s*(?:张|块|个)?\s*(?:GPU|gpu|卡)",
        r"(?:GPU|gpu)\s*[:：]?\s*(\d+)",
        r"(\d+)\s*卡(?:集群|训练|推理)?",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return None


def _parse_industry(text: str) -> str | None:
    mapping = {
        "医院": "healthcare",
        "医疗": "healthcare",
        "健康": "healthcare",
        "金融": "finance",
        "银行": "finance",
        "科研": "research",
        "高校": "education",
        "教育": "education",
        "政府": "government",
        "制造": "manufacturing",
        "互联网": "internet",
    }
    for kw, val in mapping.items():
        if kw in text:
            return val
    return None


def _parse_scenario(text: str) -> ProjectScenario | None:
    if any(k in text for k in ("推理", "inference", "问诊", "影像", "辅助诊断")):
        return ProjectScenario.INFERENCE
    if any(k in text for k in ("训练", "training", "大模型训练", "预训练")):
        return ProjectScenario.TRAINING
    if any(k in text for k in ("混合", "mixed", "训推一体", "训推")):
        return ProjectScenario.MIXED
    return None


def _parse_compliance(text: str) -> str | None:
    if "等保三" in text or "等保3" in text:
        return "等保三级"
    if "等保二" in text or "等保2" in text:
        return "等保二级"
    if "国产化" in text or "信创" in text:
        return "国产化/信创"
    return None


def _pflops_to_gpus(pflops: float, industry: str | None) -> int:
    # ~1 PFLOPS per high-end GPU (H-class FP16 order of magnitude)
    base = max(8, math.ceil(pflops * 1.2))
    if industry == "healthcare":
        return max(base, math.ceil(pflops * 2))
    return base


def _industry_default_scenario(industry: str | None) -> ProjectScenario:
    if industry == "healthcare":
        return ProjectScenario.INFERENCE
    if industry == "research":
        return ProjectScenario.TRAINING
    if industry == "finance":
        return ProjectScenario.MIXED
    return ProjectScenario.MIXED


def _suggest_name(slots: dict[str, Any]) -> str:
    industry_labels = {
        "healthcare": "智慧医疗",
        "finance": "金融",
        "research": "科研",
        "education": "教育",
        "government": "政务",
    }
    label = industry_labels.get(slots.get("industry"), "智算")
    gpus = slots.get("target_gpus")
    pflops = slots.get("compute_pflops")
    if gpus:
        return f"{label}{gpus}卡集群"
    if pflops:
        return f"{label}{pflops}P算力集群"
    return f"{label}数据中心方案"


def _extract_from_text(text: str, slots: dict[str, Any]) -> None:
    pflops = _parse_pflops(text)
    if pflops is not None:
        slots["compute_pflops"] = pflops
        if slots.get("target_gpus") is None:
            slots["target_gpus"] = _pflops_to_gpus(pflops, slots.get("industry"))

    gpus = _parse_gpu_count(text)
    if gpus is not None:
        slots["target_gpus"] = gpus

    industry = _parse_industry(text)
    if industry:
        slots["industry"] = industry

    scenario = _parse_scenario(text)
    if scenario:
        slots["scenario"] = scenario

    compliance = _parse_compliance(text)
    if compliance:
        slots["compliance"] = compliance

    if "8卡" in text or "八卡" in text:
        slots["gpus_per_node"] = 8
    if "4卡" in text or "四卡" in text:
        slots["gpus_per_node"] = 4

    if re.search(r"64\s*口|64口", text):
        slots["switch_ports"] = 64
    if re.search(r"32\s*口|32口", text):
        slots["switch_ports"] = 32


def _missing_questions(slots: dict[str, Any], asked: set[str]) -> list[str]:
    questions: list[str] = []

    if slots.get("target_gpus") is None and "gpus" not in asked:
        questions.append("请说明目标算力规模：例如「10P算力」或「128张GPU」，以便精确规划集群规模。")

    if slots.get("scenario") is None and "scenario" not in asked:
        industry = slots.get("industry")
        hint = ""
        if industry == "healthcare":
            hint = "（医疗场景通常以推理为主，如影像AI、辅助诊断）"
        questions.append(f"主要应用场景是训练、推理还是训推混合？{hint}")

    if slots.get("industry") is None and "industry" not in asked:
        questions.append("项目面向哪个行业？例如医院、金融、科研院校等，这会影响存储与高可用配置。")

    if slots.get("compliance") is None and "compliance" not in asked:
        if slots.get("industry") in ("healthcare", "finance", "government"):
            questions.append("是否有等保或国产化/信创要求？如有请说明等级。")

    if slots.get("gpus_per_node") is None and "gpus_per_node" not in asked and len(questions) < 2:
        questions.append("每节点计划配置几张 GPU？（常见为 8 卡，也可选 4 卡或 16 卡）")

    return questions[:2]


def _build_reply(slots: dict[str, Any], questions: list[str], ready: bool) -> str:
    parts: list[str] = []

    if slots.get("industry") == "healthcare":
        parts.append("已识别为**医疗行业**场景，将优先考虑推理负载、数据合规与存储冗余。")
    elif slots.get("industry"):
        parts.append(f"已识别行业标签：{slots['industry']}。")

    if slots.get("compute_pflops"):
        parts.append(
            f"目标算力约 **{slots['compute_pflops']}P**，"
            f"折算建议 GPU 规模约 **{slots.get('target_gpus', '—')} 张**。"
        )
    elif slots.get("target_gpus"):
        parts.append(f"目标 GPU 数量：**{slots['target_gpus']} 张**。")

    if slots.get("scenario"):
        scenario_cn = {
            ProjectScenario.TRAINING: "训练",
            ProjectScenario.INFERENCE: "推理",
            ProjectScenario.MIXED: "训推混合",
        }
        parts.append(f"应用场景：**{scenario_cn.get(slots['scenario'], slots['scenario'])}**。")

    if slots.get("compliance"):
        parts.append(f"合规要求：{slots['compliance']}。")

    if ready:
        parts.append("参数已足够生成初步方案，您可以点击「应用方案并生成拓扑」进入设计器。")
        if slots.get("scheme_summary"):
            parts.append(f"方案要点：{slots['scheme_summary']}")
    elif questions:
        parts.append("为生成更贴切的方案，还需要确认以下信息：")
        for i, q in enumerate(questions, 1):
            parts.append(f"{i}. {q}")
    else:
        parts.append("请继续补充需求细节，我会据此调整方案参数。")

    return "\n".join(parts)


def _normalize_scenario(value: Any) -> ProjectScenario | None:
    if value is None:
        return None
    if isinstance(value, ProjectScenario):
        return value
    text = str(value).strip().upper()
    mapping = {
        "TRAINING": ProjectScenario.TRAINING,
        "INFERENCE": ProjectScenario.INFERENCE,
        "MIXED": ProjectScenario.MIXED,
        "训练": ProjectScenario.TRAINING,
        "推理": ProjectScenario.INFERENCE,
        "混合": ProjectScenario.MIXED,
        "训推": ProjectScenario.MIXED,
        "训推混合": ProjectScenario.MIXED,
    }
    if text in mapping:
        return mapping[text]
    for key, scenario in mapping.items():
        if key in str(value):
            return scenario
    try:
        return ProjectScenario(text)
    except ValueError:
        return None


def _enrich_scheme(slots: dict[str, Any]) -> str:
    """Fill missing topology params from industry/scenario heuristics."""
    industry = slots.get("industry")
    scenario = slots.get("scenario")
    if isinstance(scenario, str):
        scenario = _normalize_scenario(scenario)
        if scenario:
            slots["scenario"] = scenario

    target_gpus = slots.get("target_gpus") or 0

    if slots.get("gpus_per_node") is None:
        slots["gpus_per_node"] = 4 if industry == "healthcare" and target_gpus <= 32 else 8

    if slots.get("switch_ports") is None:
        if target_gpus >= 256:
            slots["switch_ports"] = 64
        elif industry == "healthcare":
            slots["switch_ports"] = 32
        else:
            slots["switch_ports"] = 64

    if slots.get("network_arch") is None:
        slots["network_arch"] = "FAT_TREE"

    if slots.get("free_scheduler_with_server") is None:
        slots["free_scheduler_with_server"] = True

    parts: list[str] = []
    if industry == "healthcare":
        parts.append("医疗场景优先推理负载，建议双副本存储与等保合规网络隔离")
    elif industry == "finance":
        parts.append("金融场景建议训推混合，强化网络冗余与审计日志")
    elif industry == "research":
        parts.append("科研训练场景建议 8 卡节点与 Fat-Tree 网络")

    if scenario == ProjectScenario.INFERENCE:
        parts.append("推理为主，控制节点规模，预留弹性扩容")
    elif scenario == ProjectScenario.TRAINING:
        parts.append("训练为主，优先高带宽互联与大规模并行")

    if slots.get("compliance"):
        parts.append(f"合规：{slots['compliance']}")

    servers = math.ceil(target_gpus / slots["gpus_per_node"]) if target_gpus else 0
    if servers:
        parts.append(
            f"约 {target_gpus} 张 GPU / {slots['gpus_per_node']} 卡节点 ≈ {servers} 台服务器，"
            f"{slots['switch_ports']} 口交换机 Fat-Tree"
        )

    summary = "；".join(parts) if parts else "标准智算集群方案"
    slots["scheme_summary"] = slots.get("scheme_summary") or summary
    return slots["scheme_summary"]


def _to_extracted(slots: dict[str, Any]) -> ExtractedRequirements:
    scenario = slots.get("scenario")
    if isinstance(scenario, str):
        scenario = _normalize_scenario(scenario)

    return ExtractedRequirements(
        target_gpus=slots.get("target_gpus"),
        scenario=scenario,
        gpus_per_node=slots.get("gpus_per_node", 8),
        switch_ports=slots.get("switch_ports", 64),
        network_arch=slots.get("network_arch", "FAT_TREE"),
        free_scheduler_with_server=slots.get("free_scheduler_with_server", True),
        industry=slots.get("industry"),
        compute_pflops=slots.get("compute_pflops"),
        project_name=_suggest_name(slots),
        description=slots.get("description"),
        compliance=slots.get("compliance"),
        scheme_summary=slots.get("scheme_summary"),
    )


class RequirementConsultant:
    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        *,
        project_id: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ConsultationChatResponse:
        settings = settings or {}
        provider = settings.get("provider", ConsultationProvider.RULE.value)

        if provider == ConsultationProvider.OPENAI_COMPATIBLE.value:
            api_key = settings.get("api_key", "")
            if api_key:
                try:
                    return await self._chat_with_llm(
                        message, session_id, project_id=project_id, settings=settings
                    )
                except Exception as exc:
                    raise ValidationError(f"LLM 咨询失败：{exc}") from exc
            return self._chat_with_rules(
                message,
                session_id,
                project_id=project_id,
                engine_hint=(
                    "当前为 OpenAI 兼容模式但未配置 API Key，暂用规则引擎回复。"
                    "管理员可在「设置 → 智能需求咨询」中填写 API Key 与模型名称，"
                    "以获得更智能的个性化方案建议。"
                ),
            )

        return self._chat_with_rules(message, session_id, project_id=project_id)

    async def chat_stream(
        self,
        message: str,
        session_id: str | None = None,
        *,
        project_id: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        settings = settings or {}
        provider = settings.get("provider", ConsultationProvider.RULE.value)
        use_llm = (
            provider == ConsultationProvider.OPENAI_COMPATIBLE.value
            and bool(settings.get("api_key"))
        )

        try:
            if use_llm:
                async for event in self._chat_stream_llm(
                    message, session_id, project_id=project_id, settings=settings
                ):
                    yield event
            else:
                engine_hint = None
                if provider == ConsultationProvider.OPENAI_COMPATIBLE.value:
                    engine_hint = (
                        "当前为 OpenAI 兼容模式但未配置 API Key，暂用规则引擎回复。"
                        "管理员可在「设置 → 智能需求咨询」中填写 API Key 与模型名称。"
                    )
                response = self._chat_with_rules(
                    message,
                    session_id,
                    project_id=project_id,
                    engine_hint=engine_hint,
                )
                for chunk in _stream_text_chunks(response.reply):
                    yield {"type": "token", "delta": chunk}
                yield {"type": "done", "data": response.model_dump(mode="json")}
        except ValidationError as exc:
            yield {"type": "error", "message": str(exc.detail)}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)}

    def _chat_with_rules(
        self,
        message: str,
        session_id: str | None = None,
        *,
        project_id: str | None = None,
        engine_hint: str | None = None,
    ) -> ConsultationChatResponse:
        session, session_id = _get_or_create_session(project_id, session_id)
        _append_user_message(session, message)

        _extract_from_text(message, session.slots)
        enrich_slots_from_message(message, session.slots)

        if session.slots.get("scenario") is None:
            mapped = _intent_to_scenario(session.slots.get("intent"))
            if mapped:
                session.slots["scenario"] = mapped
            elif session.slots.get("industry"):
                session.slots["scenario"] = _industry_default_scenario(session.slots["industry"])

        turn = _planner.plan_turn(
            message,
            session.slots,
            session.asked,
            context_lines=_planner_context_lines(session.slots),
        )
        session.asked.update(turn.asked_keys)

        ready = turn.ready and session.slots.get("target_gpus") is not None
        questions = turn.questions

        if ready:
            _enrich_scheme(session.slots)

        reply = turn.reply
        if engine_hint and not any(m.role == "assistant" for m in session.messages):
            reply = f"{engine_hint}\n\n{reply}"
        session.messages.append(ConsultationMessage(role="assistant", content=reply))

        extracted = _to_extracted(session.slots) if ready else None

        return ConsultationChatResponse(
            session_id=session_id,
            reply=reply,
            questions=questions,
            ready_to_generate=ready,
            extracted=extracted,
            messages=session.messages,
            engine="rule",
            intent=turn.classification.intent.value,
            intent_confidence=turn.classification.confidence,
            needs_clarification=turn.classification.needs_clarification,
            diagnostic_questions=turn.diagnostic_questions,
        )

    async def _chat_with_llm(
        self,
        message: str,
        session_id: str | None,
        *,
        project_id: str | None = None,
        settings: dict[str, Any],
    ) -> ConsultationChatResponse:
        session, session_id = _get_or_create_session(project_id, session_id)
        _append_user_message(session, message)

        system_prompt = self._build_llm_system_prompt(settings)
        llm_messages = self._build_llm_messages(session, system_prompt)

        response = await post_llm_chat_completion(
            api_base_url=settings["api_base_url"],
            api_key=settings["api_key"],
            model=settings["model"],
            timeout_seconds=settings.get("timeout_seconds", 60),
            messages=llm_messages,
        )
        if response.status_code >= 400:
            raise ValidationError(
                format_llm_api_error(
                    response.status_code, response.text, settings.get("api_base_url", "")
                )
            )

        content = response.json()["choices"][0]["message"]["content"]
        return self._finalize_llm_response(session, session_id, message, content)

    async def _chat_stream_llm(
        self,
        message: str,
        session_id: str | None,
        *,
        project_id: str | None = None,
        settings: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        session, session_id = _get_or_create_session(project_id, session_id)
        _append_user_message(session, message)

        system_prompt = self._build_llm_system_prompt(settings)
        llm_messages = self._build_llm_messages(session, system_prompt)

        content_parts: list[str] = []
        reply_extractor = ReplyFieldExtractor()
        async for delta in stream_llm_chat_completion(
            api_base_url=settings["api_base_url"],
            api_key=settings["api_key"],
            model=settings["model"],
            timeout_seconds=settings.get("timeout_seconds", 60),
            messages=llm_messages,
        ):
            content_parts.append(delta)
            display_delta = reply_extractor.feed(delta)
            if display_delta:
                yield {"type": "token", "delta": display_delta}

        content = "".join(content_parts)
        result = self._finalize_llm_response(session, session_id, message, content)
        yield {"type": "done", "data": result.model_dump(mode="json")}

    def _build_llm_system_prompt(self, settings: dict[str, Any]) -> str:
        return (
            f"{settings.get('system_prompt', '')}\n\n"
            "请以 JSON 回复，格式示例："
            '{"reply":"给用户的中文回复","questions":["追问1"],"ready_to_generate":false,'
            '"scheme_summary":"方案一句话摘要",'
            '"slots":{"target_gpus":128,"scenario":"INFERENCE","industry":"healthcare",'
            '"compute_pflops":10,"gpus_per_node":8,"switch_ports":64,'
            '"network_arch":"FAT_TREE","free_scheduler_with_server":true,'
            '"compliance":"等保三级","project_name":"智慧医疗128卡集群"}}'
        )

    def _build_llm_messages(
        self, session: ConsultationSession, system_prompt: str
    ) -> list[dict[str, str]]:
        llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for msg in session.messages[-10:]:
            llm_messages.append({"role": msg.role, "content": msg.content})
        return llm_messages

    def _finalize_llm_response(
        self,
        session: ConsultationSession,
        session_id: str,
        message: str,
        content: str,
    ) -> ConsultationChatResponse:
        parsed = parse_llm_json_reply(content) or {}

        reply = parsed.get("reply") or content
        questions = parsed.get("questions") or []
        ready = bool(parsed.get("ready_to_generate"))
        slots_data = parsed.get("slots") or {}
        scheme_summary = parsed.get("scheme_summary")

        for key, value in slots_data.items():
            if value is not None:
                session.slots[key] = value
        if scheme_summary:
            session.slots["scheme_summary"] = scheme_summary
        _extract_from_text(message, session.slots)

        required = ("target_gpus", "scenario", "industry")
        if ready and not all(session.slots.get(k) for k in required):
            ready = False
            if not questions:
                questions = _missing_questions(session.slots, session.asked)

        if not parsed:
            questions = _missing_questions(session.slots, session.asked)
            ready = len(questions) == 0 and session.slots.get("target_gpus") is not None
            reply = _build_reply(session.slots, questions, ready)
        elif ready:
            _enrich_scheme(session.slots)
            if scheme_summary:
                session.slots["scheme_summary"] = scheme_summary

        display_reply = self._format_display_reply(reply, questions, ready)
        session.messages.append(ConsultationMessage(role="assistant", content=display_reply))
        extracted = _to_extracted(session.slots) if ready else None

        return ConsultationChatResponse(
            session_id=session_id,
            reply=display_reply,
            questions=questions,
            ready_to_generate=ready,
            extracted=extracted,
            messages=session.messages,
            engine="openai_compatible",
        )

    def _format_display_reply(self, reply: str, questions: list[str], ready: bool) -> str:
        parts = [reply.strip()] if reply.strip() else []
        if questions and not ready:
            qs = [q for q in questions if q and q not in reply]
            if qs:
                parts.append("为生成更贴切的方案，还需要确认：")
                parts.extend(f"{i}. {q}" for i, q in enumerate(qs, 1))
        if ready and parts:
            parts.append("参数已足够生成初步方案，您可以点击「应用方案并生成拓扑」。")
        return "\n".join(parts)
