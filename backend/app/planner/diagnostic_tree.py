"""Dynamic diagnostic follow-up chains per intent — deterministic, no LLM."""

from __future__ import annotations

from dataclasses import dataclass

from app.planner.intent_classifier import Intent


@dataclass(frozen=True)
class DiagnosticNode:
    slot_key: str
    question_key: str
    engineering_constraint: str
    engineering_purpose: str
    required: bool = True


DIAGNOSTIC_TREES: dict[Intent, list[DiagnosticNode]] = {
    Intent.PRETRAIN: [
        DiagnosticNode(
            slot_key="token_scale_monthly",
            question_key="token_scale",
            engineering_constraint="affects_storage_checkpoint",
            engineering_purpose="月 Token 处理量决定并行文件系统容量与 checkpoint 频率设计",
        ),
        DiagnosticNode(
            slot_key="parallel_strategy",
            question_key="parallel_strategy",
            engineering_constraint="affects_nvlink_topology",
            engineering_purpose="数据并行 vs 模型/流水线并行直接影响 NVLink 拓扑与 Spine 收敛比",
        ),
        DiagnosticNode(
            slot_key="target_gpus",
            question_key="gpu_scale",
            engineering_constraint="affects_fat_tree_radix",
            engineering_purpose="GPU 规模决定 Fat-Tree 层数与 Leaf/Spine 数量",
        ),
        DiagnosticNode(
            slot_key="compliance",
            question_key="compliance",
            engineering_constraint="affects_network_isolation",
            engineering_purpose="等保/信创要求影响网络分区与设备选型边界",
            required=False,
        ),
    ],
    Intent.SFT: [
        DiagnosticNode(
            slot_key="base_model_params",
            question_key="base_model",
            engineering_constraint="affects_gpu_memory",
            engineering_purpose="基座参数量级决定单卡显存下限与是否需张量并行",
        ),
        DiagnosticNode(
            slot_key="finetune_dataset_size",
            question_key="dataset_size",
            engineering_constraint="affects_storage_throughput",
            engineering_purpose="微调数据集规模影响存储吞吐与数据加载并行度",
        ),
        DiagnosticNode(
            slot_key="target_gpus",
            question_key="gpu_scale",
            engineering_constraint="affects_fat_tree_radix",
            engineering_purpose="训练节点规模影响网络收敛比与作业调度粒度",
        ),
    ],
    Intent.RLHF: [
        DiagnosticNode(
            slot_key="rlhf_stages",
            question_key="rlhf_pipeline",
            engineering_constraint="affects_cluster_partition",
            engineering_purpose="奖励模型/策略模型/参考模型是否分集群影响网络隔离设计",
        ),
        DiagnosticNode(
            slot_key="target_gpus",
            question_key="gpu_scale",
            engineering_constraint="affects_fat_tree_radix",
            engineering_purpose="多阶段流水线需要预留跨域高带宽与弹性调度能力",
        ),
        DiagnosticNode(
            slot_key="inference_qps_peak",
            question_key="inference_qps",
            engineering_constraint="affects_mixed_load_scheduling",
            engineering_purpose="在线推理峰值决定训推混部时的资源预留比例",
            required=False,
        ),
    ],
    Intent.INFERENCE: [
        DiagnosticNode(
            slot_key="inference_qps_peak",
            question_key="qps_peak",
            engineering_constraint="affects_gpu_count",
            engineering_purpose="峰值 QPS 是推理节点数与批处理策略的核心输入",
            required=False,
        ),
        DiagnosticNode(
            slot_key="latency_p99_ms",
            question_key="latency_p99",
            engineering_constraint="affects_network_latency",
            engineering_purpose="P99 延迟目标决定是否需要本地化部署与 RDMA 低时延网络",
            required=False,
        ),
        DiagnosticNode(
            slot_key="target_gpus",
            question_key="gpu_scale",
            engineering_constraint="affects_fat_tree_radix",
            engineering_purpose="并发规模影响 Leaf 接入密度与弹性扩缩策略",
            required=False,
        ),
        DiagnosticNode(
            slot_key="compliance",
            question_key="compliance",
            engineering_constraint="affects_network_isolation",
            engineering_purpose="等保/信创要求影响网络分区与设备选型边界",
            required=False,
        ),
    ],
    Intent.GENERAL: [
        DiagnosticNode(
            slot_key="workload_type",
            question_key="workload_type",
            engineering_constraint="affects_intent_routing",
            engineering_purpose="明确 workload 类型后才能选择正确的诊断链与拓扑模板",
        ),
        DiagnosticNode(
            slot_key="target_gpus",
            question_key="gpu_scale",
            engineering_constraint="affects_fat_tree_radix",
            engineering_purpose="算力规模是网络与存储容量的基础约束",
        ),
        DiagnosticNode(
            slot_key="industry",
            question_key="industry",
            engineering_constraint="affects_compliance_defaults",
            engineering_purpose="行业属性决定默认合规等级与存储冗余策略",
            required=False,
        ),
    ],
}


def next_diagnostic_nodes(
    intent: Intent,
    slots: dict,
    asked: set[str],
    *,
    limit: int = 2,
) -> list[DiagnosticNode]:
    """Return the next unanswered required diagnostic nodes; optional fill remaining quota."""
    tree = DIAGNOSTIC_TREES.get(intent, DIAGNOSTIC_TREES[Intent.GENERAL])
    required_pending: list[DiagnosticNode] = []
    optional_pending: list[DiagnosticNode] = []

    for node in tree:
        if node.question_key in asked:
            continue
        if slots.get(node.slot_key) is not None:
            continue
        if node.required:
            required_pending.append(node)
        else:
            optional_pending.append(node)

    pending = required_pending[:limit]
    if len(pending) < limit:
        pending.extend(optional_pending[: limit - len(pending)])
    return pending
