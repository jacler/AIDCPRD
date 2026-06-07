"""Dynamic security compliance checklist (等保等) — deterministic rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ChecklistItem:
    item_id: str
    title: str
    status: CheckStatus
    remediation: str
    regulation_ref: str
    engineering_note: str

    @property
    def status_icon(self) -> str:
        return {"pass": "✅", "warn": "⚠️", "fail": "❌"}[self.status.value]


def _has(text: str | None, *keywords: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def generate_security_checklist(context: dict[str, Any]) -> list[ChecklistItem]:
    """Build checklist from architecture context (industry, compliance, topology flags)."""
    items: list[ChecklistItem] = []
    compliance = str(context.get("compliance") or "")
    industry = str(context.get("industry") or "")
    domestic_mode = bool(context.get("domestic_mode"))
    cross_domain = bool(context.get("cross_domain"))
    has_audit_log = bool(context.get("audit_logging_enabled"))
    network_zoned = bool(context.get("network_zoned"))
    target_gpus = int(context.get("target_gpus") or 0)

    level3 = _has(compliance, "等保三", "等保3", "level 3")
    level2 = _has(compliance, "等保二", "等保2", "level 2")
    xinchuang = domestic_mode or _has(compliance, "信创", "国产化")

    # GB/T 22239-2019 — 安全通信网络 / 安全区域边界
    if level3 or cross_domain:
        status = CheckStatus.PASS if network_zoned else CheckStatus.FAIL
        items.append(
            ChecklistItem(
                item_id="boundary_protection",
                title="安全区域边界防护与网络分区",
                status=status,
                remediation="划分计算区/管理区/存储区 VLAN/VXLAN；部署下一代防火墙与东西向微隔离",
                regulation_ref="GB/T 22239-2019 安全区域边界（第 7.1.3 章）",
                engineering_note="跨域或等保三级场景必须实现逻辑隔离与访问控制策略",
            )
        )
    elif level2:
        items.append(
            ChecklistItem(
                item_id="boundary_protection",
                title="安全区域边界基础防护",
                status=CheckStatus.WARN if not network_zoned else CheckStatus.PASS,
                remediation="至少实现管理网与业务网分离，关键链路 ACL 管控",
                regulation_ref="GB/T 22239-2019 安全区域边界",
                engineering_note="等保二级建议完成基础分区",
            )
        )

    # 安全审计
    audit_status = CheckStatus.PASS if has_audit_log else (
        CheckStatus.FAIL if level3 else CheckStatus.WARN
    )
    items.append(
        ChecklistItem(
            item_id="security_audit",
            title="安全审计与日志留存",
            status=audit_status,
            remediation="启用集中日志（≥180 天留存）；覆盖登录、特权操作、策略变更",
            regulation_ref="GB/T 22239-2019 安全审计（第 7.1.4 章）",
            engineering_note="等保测评必查项，需与 SIEM 对接",
        )
    )

    # 身份鉴别 / 访问控制
    items.append(
        ChecklistItem(
            item_id="access_control",
            title="身份鉴别与访问控制",
            status=CheckStatus.WARN,
            remediation="管理面启用 MFA；RBAC 最小权限；禁用默认口令",
            regulation_ref="GB/T 22239-2019 安全计算环境（第 7.1.5 章）",
            engineering_note="K8s/调度平台与带外管理均需纳入",
        )
    )

    if industry == "healthcare" or _has(industry, "医疗", "healthcare"):
        items.append(
            ChecklistItem(
                item_id="health_data_localization",
                title="医疗健康数据本地化与脱敏",
                status=CheckStatus.WARN,
                remediation="患者数据不出域；推理链路脱敏；存储加密（国密算法优先）",
                regulation_ref="《数据安全法》+ 卫生健康行业数据分类分级指南",
                engineering_note="医疗影像 AI 需额外关注 DICOM 元数据保护",
            )
        )

    if xinchuang:
        items.append(
            ChecklistItem(
                item_id="domestic_stack",
                title="信创软硬件栈与供应链可控",
                status=CheckStatus.WARN,
                remediation="关键组件国产化替代清单化；保留兼容性验证与回退预案",
                regulation_ref="信创产业标准体系（公开政策文件）",
                engineering_note="需同步完成框架-算力兼容性评估",
            )
        )

    if target_gpus >= 256:
        items.append(
            ChecklistItem(
                item_id="dr_bcp",
                title="大规模集群容灾与业务连续性",
                status=CheckStatus.WARN,
                remediation="定义 RPO/RTO；跨可用区 checkpoint；关键元数据多副本",
                regulation_ref="GB/T 22239-2019 安全建设管理",
                engineering_note="千卡规模建议双机房或双 AZ 架构评审",
            )
        )

    if cross_domain:
        items.append(
            ChecklistItem(
                item_id="cross_domain_exchange",
                title="跨域数据交换与接口安全",
                status=CheckStatus.FAIL if not network_zoned else CheckStatus.WARN,
                remediation="跨域链路加密（TLS/IPsec）；接口鉴权与流量审计",
                regulation_ref="GB/T 22239-2019 安全通信网络",
                engineering_note="跨域部署触发边界防护加强检查",
            )
        )

    return items
