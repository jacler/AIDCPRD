"""Compliance evaluation orchestrator."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.compliance.audit_logger import ComplianceAuditLogger
from app.compliance.domestic_adapter import adapt_catalog_items, check_framework_compatibility
from app.compliance.security_checklist import ChecklistItem, CheckStatus, generate_security_checklist


class ComplianceService:
    def evaluate(
        self,
        *,
        project_name: str,
        target_gpus: int,
        compliance: str | None = None,
        industry: str | None = None,
        domestic_mode: bool = False,
        frameworks: list[str] | None = None,
        bom_items: list[dict[str, str]] | None = None,
        cross_domain: bool = False,
        network_zoned: bool = False,
        audit_logging_enabled: bool = False,
    ) -> dict[str, Any]:
        logger = ComplianceAuditLogger()
        frameworks = frameworks or ["pytorch"]

        logger.log(
            "input_validation",
            "accepted",
            domestic_mode=domestic_mode,
            frameworks=frameworks,
            compliance=compliance or "未指定",
        )

        adaptation = adapt_catalog_items(
            bom_items or [],
            domestic_mode=domestic_mode,
            frameworks=frameworks,
        )

        if domestic_mode:
            logger.log(
                "domestic_substitution",
                f"替换 {len(adaptation.replacements)} 项",
                unmatched=len(adaptation.unmatched),
            )
            for gap in adaptation.compatibility_gaps:
                logger.log(
                    "framework_compatibility",
                    f"{gap.framework}: {gap.status}",
                    gap=gap.compatibility_gap,
                    remediation=gap.remediation,
                )
        else:
            for fw in frameworks:
                gap = check_framework_compatibility(fw, "NVIDIA")
                if gap:
                    logger.log(
                        "framework_compatibility",
                        f"{fw}: {gap.status}",
                        gap=gap.compatibility_gap,
                    )

        checklist = generate_security_checklist(
            {
                "compliance": compliance,
                "industry": industry,
                "domestic_mode": domestic_mode,
                "cross_domain": cross_domain,
                "network_zoned": network_zoned,
                "audit_logging_enabled": audit_logging_enabled,
                "target_gpus": target_gpus,
            }
        )

        for item in checklist:
            logger.log(
                "security_checklist",
                f"{item.item_id}: {item.status.value}",
                title=item.title,
                regulation=item.regulation_ref,
            )

        fail_count = sum(1 for i in checklist if i.status == CheckStatus.FAIL)
        warn_count = sum(1 for i in checklist if i.status == CheckStatus.WARN)
        overall = "fail" if fail_count else ("warn" if warn_count else "pass")

        logger.log("overall_assessment", overall, fail=fail_count, warn=warn_count)

        return {
            "project_name": project_name,
            "overall_status": overall,
            "domestic_adaptation": {
                "enabled": adaptation.enabled,
                "replacements": [asdict(r) for r in adaptation.replacements],
                "unmatched": adaptation.unmatched,
                "compatibility_gaps": [asdict(g) for g in adaptation.compatibility_gaps],
                "frameworks_requested": adaptation.frameworks_requested,
            },
            "security_checklist": [_checklist_to_dict(i) for i in checklist],
            "audit_trail": logger.to_dict_list(),
            "appendix_markdown": logger.to_appendix_markdown(project_name=project_name),
        }


def _checklist_to_dict(item: ChecklistItem) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "title": item.title,
        "status": item.status.value,
        "status_icon": item.status_icon,
        "remediation": item.remediation,
        "regulation_ref": item.regulation_ref,
        "engineering_note": item.engineering_note,
    }
