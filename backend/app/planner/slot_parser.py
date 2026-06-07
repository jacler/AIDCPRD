"""Parse user replies into planner slot values — deterministic only."""

from __future__ import annotations

import re


def enrich_slots_from_message(text: str, slots: dict) -> None:
    normalized = text.strip()

    if re.search(r"数据并行|data\s*parallel|dp\b", normalized, re.I):
        slots["parallel_strategy"] = "data_parallel"
    elif re.search(r"模型并行|流水线|tensor\s*parallel|tp\b|pp\b", normalized, re.I):
        slots["parallel_strategy"] = "model_or_pipeline_parallel"

    token_match = re.search(
        r"(\d+(?:\.\d+)?)\s*[tT](?:oken)?(?:/月|每月|一个月)?", normalized
    )
    if token_match:
        slots["token_scale_monthly"] = f"{token_match.group(1)}T"

    qps_match = re.search(r"(\d+)\s*(?:qps|QPS|请求/秒)", normalized)
    if qps_match:
        slots["inference_qps_peak"] = int(qps_match.group(1))

    latency_match = re.search(r"p99[^\d]*(\d+)\s*ms", normalized, re.I)
    if latency_match:
        slots["latency_p99_ms"] = int(latency_match.group(1))

    if re.search(r"预训练|pretrain", normalized, re.I):
        slots["workload_type"] = "pretrain"
    elif re.search(r"微调|sft", normalized, re.I):
        slots["workload_type"] = "sft"
    elif re.search(r"rlhf|对齐", normalized, re.I):
        slots["workload_type"] = "rlhf"
    elif re.search(r"推理|inference", normalized, re.I):
        slots["workload_type"] = "inference"

    params_match = re.search(r"(\d+(?:\.\d+)?)\s*[bB](?:参数|参)?", normalized)
    if params_match:
        slots["base_model_params"] = f"{params_match.group(1)}B"
