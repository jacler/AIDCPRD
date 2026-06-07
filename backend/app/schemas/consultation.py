from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.hardware import ProjectScenario

from app.schemas.api import GenerateTopologyResponse


class ConsultationMessage(BaseModel):
    role: str
    content: str


class ConsultationChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    project_id: UUID | None = None


class ExtractedRequirements(BaseModel):
    target_gpus: int | None = None
    scenario: ProjectScenario | None = None
    gpus_per_node: int | None = None
    switch_ports: int | None = None
    network_arch: str | None = None
    free_scheduler_with_server: bool | None = None
    industry: str | None = None
    compute_pflops: float | None = None
    project_name: str | None = None
    description: str | None = None
    compliance: str | None = None
    scheme_summary: str | None = None


class DiagnosticQuestion(BaseModel):
    slot_key: str
    text: str
    engineering_constraint: str
    engineering_purpose: str


class ConsultationChatResponse(BaseModel):
    session_id: str
    reply: str
    questions: list[str] = Field(default_factory=list)
    ready_to_generate: bool = False
    extracted: ExtractedRequirements | None = None
    messages: list[ConsultationMessage] = Field(default_factory=list)
    engine: str = "rule"
    intent: str | None = None
    intent_confidence: float | None = None
    needs_clarification: bool = False
    diagnostic_questions: list[DiagnosticQuestion] = Field(default_factory=list)


class UpdateTopologyRequest(BaseModel):
    compute: dict[str, int] | None = None
    network: dict[str, int] | None = None
    storage: dict[str, int] | None = None
    graph_layout: dict[str, Any] | None = None
    scenario: ProjectScenario | None = None


class ApplyPlanRequest(BaseModel):
    extracted: ExtractedRequirements
    project_id: UUID | None = None
    requirement_text: str | None = None
    import_skus: bool = True


class ApplyPlanResponse(BaseModel):
    project_id: UUID
    project_name: str
    ready_to_generate: bool = True
    topology: dict[str, Any] | None = None
    topology_result: GenerateTopologyResponse | None = None
    bom_count: int = 0
    skus_imported: int = 0
    sku_search_note: str = ""
    message: str = ""
