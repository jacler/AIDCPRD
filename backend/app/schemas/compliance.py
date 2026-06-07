from typing import Any

from pydantic import BaseModel, Field


class ComplianceEvaluateRequest(BaseModel):
    domestic_mode: bool = False
    frameworks: list[str] = Field(default_factory=lambda: ["pytorch"])
    compliance: str | None = None
    industry: str | None = None
    cross_domain: bool = False
    network_zoned: bool = False
    audit_logging_enabled: bool = False


class ComplianceEvaluateResponse(BaseModel):
    project_id: str | None = None
    project_name: str
    overall_status: str
    domestic_adaptation: dict[str, Any]
    security_checklist: list[dict[str, Any]]
    audit_trail: list[dict[str, Any]]
    appendix_markdown: str
