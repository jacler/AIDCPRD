"""Deterministic intent classifier — no LLM for classification logic."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    PRETRAIN = "pretrain"
    SFT = "sft"
    RLHF = "rlhf"
    INFERENCE = "inference"
    GENERAL = "general"


CLARIFICATION_THRESHOLD = 0.8

# (pattern, intent, base_score) — higher score = stronger signal
_INTENT_SIGNALS: list[tuple[str, Intent, float]] = [
    (r"预训练|pretrain|pre-train|从零训练|基座模型", Intent.PRETRAIN, 0.92),
    (r"大模型训练|训.*大模型|训练.*LLM|千亿|万亿", Intent.PRETRAIN, 0.78),
    (r"微调|fine[- ]?tune|sft|监督微调|领域适配", Intent.SFT, 0.9),
    (r"rlhf|人类反馈|对齐|dpo|偏好学习", Intent.RLHF, 0.92),
    (r"推理|inference|问答|qps|延迟|p99|在线服务|部署", Intent.INFERENCE, 0.88),
    (r"影像|辅助诊断|ct|问诊|问诊机器人", Intent.INFERENCE, 0.82),
    (r"医院|医疗|健康", Intent.INFERENCE, 0.7),
    (r"训推|混合|mixed", Intent.GENERAL, 0.55),
    (r"训|训练|training", Intent.PRETRAIN, 0.62),
    (r"算力|集群|数据中心|idc|gpu", Intent.GENERAL, 0.45),
]


@dataclass
class IntentClassification:
    intent: Intent
    confidence: float
    needs_clarification: bool
    clarification_hints: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


def _normalize(text: str) -> str:
    return text.strip().lower()


def classify_intent(
    text: str,
    *,
    prior_intent: str | None = None,
    slot_context: dict | None = None,
) -> IntentClassification:
    """Rule-based intent classification with confidence scoring."""
    context_bits: list[str] = []
    if slot_context:
        if slot_context.get("industry") == "healthcare":
            context_bits.append("医疗推理场景")
        if slot_context.get("scenario") in ("INFERENCE", "TRAINING", "MIXED"):
            context_bits.append(str(slot_context["scenario"]))
        if slot_context.get("workload_type"):
            context_bits.append(str(slot_context["workload_type"]))
    normalized = _normalize(" ".join([text, *context_bits]))
    scores: dict[Intent, float] = {intent: 0.0 for intent in Intent}

    for pattern, intent, weight in _INTENT_SIGNALS:
        if re.search(pattern, normalized, re.IGNORECASE):
            scores[intent] = max(scores[intent], weight)

    if prior_intent:
        try:
            prior = Intent(prior_intent)
            scores[prior] = min(1.0, scores[prior] + 0.15)
        except ValueError:
            pass

    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    if best_score < 0.4:
        best_intent = Intent.GENERAL
        best_score = 0.35

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
    if best_score - second_score < 0.12 and best_score < 0.85:
        best_score = max(0.4, best_score - 0.1)

    needs_clarification = best_score < CLARIFICATION_THRESHOLD
    hints = _clarification_hints(best_intent, normalized, needs_clarification)

    return IntentClassification(
        intent=best_intent,
        confidence=round(best_score, 3),
        needs_clarification=needs_clarification,
        clarification_hints=hints,
        scores={k.value: round(v, 3) for k, v in scores.items()},
    )


def _clarification_hints(intent: Intent, text: str, needs: bool) -> list[str]:
    if not needs:
        return []

    if intent == Intent.PRETRAIN or "大模型" in text or "训" in text:
        return [
            "请明确是预训练（Pretrain）、监督微调（SFT）还是 RLHF 对齐阶段",
            "不同训练阶段对显存、互联带宽和存储 checkpoint 策略差异显著",
        ]
    if intent == Intent.INFERENCE:
        return [
            "请补充峰值 QPS 或并发请求规模",
            "请说明 P99 延迟目标（毫秒级还是秒级）",
        ]
    if intent == Intent.SFT:
        return [
            "请说明基座模型参数量级与微调数据规模",
            "是否需要在同一集群上混部推理服务",
        ]
    if intent == Intent.RLHF:
        return [
            "请确认是否包含奖励模型与策略模型双集群部署",
            "对训练-推理混部比例是否有硬性约束",
        ]
    return [
        "请说明主要 workload 类型：预训练 / 微调 / 推理 / 训推混合",
        "请补充目标算力规模（GPU 张数或 PFLOPS）",
    ]
