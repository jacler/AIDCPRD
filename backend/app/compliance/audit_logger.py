"""Compliance audit trail — records decisions for export appendix."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEntry:
    timestamp: str
    step: str
    decision: str
    evidence: dict[str, Any] = field(default_factory=dict)


class ComplianceAuditLogger:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(self, step: str, decision: str, **evidence: Any) -> None:
        self._entries.append(
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                step=step,
                decision=decision,
                evidence=evidence,
            )
        )

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [
            {
                "timestamp": e.timestamp,
                "step": e.step,
                "decision": e.decision,
                "evidence": e.evidence,
            }
            for e in self._entries
        ]

    def to_appendix_markdown(self, *, project_name: str = "项目") -> str:
        lines = [
            f"## 合规判定依据附录 — {project_name}",
            "",
            "> 本附录由系统自动生成，记录合规评估的判定步骤与依据。",
            "> 基于公开标准与公开兼容性数据，仅供技术参考。",
            "",
            "| 时间 (UTC) | 步骤 | 判定 | 依据摘要 |",
            "| --- | --- | --- | --- |",
        ]
        for e in self._entries:
            summary = "; ".join(f"{k}={v}" for k, v in list(e.evidence.items())[:3])
            if len(summary) > 120:
                summary = summary[:117] + "..."
            lines.append(f"| {e.timestamp[:19]} | {e.step} | {e.decision} | {summary} |")

        lines.extend(["", "### 免责声明", "", "本方案基于公开数据生成，仅供技术参考。"])
        return "\n".join(lines)
