"""Consultant-style response templates — phrasing only, no rule logic."""

from __future__ import annotations

from app.planner.diagnostic_tree import DiagnosticNode
from app.planner.intent_classifier import Intent, IntentClassification


def opening_for_intent(classification: IntentClassification) -> str:
    intent = classification.intent
    confidence = classification.confidence

    labels = {
        Intent.PRETRAIN: "大规模预训练",
        Intent.SFT: "监督微调（SFT）",
        Intent.RLHF: "RLHF 对齐训练",
        Intent.INFERENCE: "在线推理服务",
        Intent.GENERAL: "通用智算",
    }
    label = labels.get(intent, "智算")

    if classification.needs_clarification:
        return (
            f"初步判断您的需求偏向 **{label}** 场景（置信度 {confidence:.0%}），"
            f"但信息还不够完整，需要再确认几个关键点，以便给出可落地的架构建议。"
        )
    return (
        f"已识别为 **{label}** 场景（置信度 {confidence:.0%}），"
        f"接下来我会围绕该场景的工程约束做针对性诊断。"
    )


def clarification_block(hints: list[str]) -> str:
    if not hints:
        return ""
    lines = ["**建议先澄清的方向：**"]
    lines.extend(f"- {h}" for h in hints)
    return "\n".join(lines)


def format_diagnostic_question(node: DiagnosticNode) -> str:
    """Map diagnostic node to consultant-style question text."""
    templates: dict[str, str] = {
        "token_scale": (
            "为了评估并行存储与 checkpoint 策略，需要确认："
            "您预计每月处理的 Token 规模大约是多少（例如 1T / 10T）？"
        ),
        "parallel_strategy": (
            "为了给您更精准的显存配比与互联设计，需要确认一下："
            "训练任务更偏向**数据并行**还是**模型/流水线并行**？"
            "这会直接影响 NVLink 拓扑与 Spine 收敛比选型。"
        ),
        "gpu_scale": (
            "请说明目标算力规模：例如「512 张 GPU」或「约 50P 算力」，"
            "这是 Fat-Tree 网络层数与 Leaf 数量的核心输入。"
        ),
        "compliance": (
            "项目是否有等保、信创或跨域部署等合规要求？"
            "这将决定网络分区边界与设备选型范围。"
        ),
        "base_model": (
            "微调所基于的基座模型大约多少参数量（如 7B / 70B / 405B）？"
            "这决定了单卡显存下限及是否必须引入张量并行。"
        ),
        "dataset_size": (
            "微调数据集大约多少 Token 或样本量？"
            "数据加载吞吐会影响存储平面与数据管道的并行度设计。"
        ),
        "rlhf_pipeline": (
            "RLHF 流水线中，奖励模型、策略模型与参考模型是否计划部署在同一集群？"
            "分集群部署需要额外的跨域带宽与作业调度隔离。"
        ),
        "inference_qps": (
            "训推混部场景下，在线推理的峰值 QPS 大约多少？"
            "这决定了需要为推理预留多少算力份额。"
        ),
        "qps_peak": (
            "为估算推理节点规模，请提供峰值 QPS 或并发会话数（例如 500 QPS）。"
        ),
        "latency_p99": (
            "对端到端 P99 延迟有无明确 SLA（例如 <200ms）？"
            "毫秒级 SLA 通常需要本地化部署与低时延 RDMA 网络。"
        ),
        "workload_type": (
            "请明确主要 workload：预训练、SFT 微调、RLHF 对齐，还是在线推理？"
            "不同阶段的显存、网络与存储约束差异很大。"
        ),
        "industry": (
            "项目面向哪个行业（医疗、金融、科研、政务等）？"
            "行业属性会影响默认合规等级与高可用配置。"
        ),
    }
    return templates.get(
        node.question_key,
        f"请补充「{node.slot_key}」相关信息，以便完善架构设计。",
    )


def engineering_purpose_line(node: DiagnosticNode) -> str:
    return f"📐 **工程目的**：{node.engineering_purpose}"


def build_consultant_reply(
    classification: IntentClassification,
    diagnostic_nodes: list[DiagnosticNode],
    *,
    context_lines: list[str] | None = None,
    ready: bool = False,
) -> str:
    parts: list[str] = [opening_for_intent(classification)]

    if context_lines:
        parts.extend(context_lines)

    if classification.needs_clarification and classification.clarification_hints:
        parts.append(clarification_block(classification.clarification_hints))

    if diagnostic_nodes and not ready:
        parts.append("为生成可落地的集群方案，还需要确认以下信息：")
        for i, node in enumerate(diagnostic_nodes, 1):
            parts.append(f"\n**{i}.** {format_diagnostic_question(node)}")
            parts.append(engineering_purpose_line(node))

    if ready:
        parts.append(
            "\n参数已足够生成初步方案，您可以点击「应用方案并生成拓扑」进入设计器。"
        )

    return "\n".join(parts)
