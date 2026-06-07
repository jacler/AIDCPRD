from typing import Any

from pydantic import BaseModel, Field


class DiagramGenerateRequest(BaseModel):
    requirement: str = ""
    pattern_id: str | None = None
    target_gpus: int | None = None
    scenario: str | None = None
    convergence_ratio: str | None = None
    device_overrides: dict[str, str] = Field(default_factory=dict)
    liquid_cooling: bool = False
    domestic_mode: bool = False
    export_mode: str = "web_interactive"
    figure_no: str = "3-2"


class DiagramGenerateResponse(BaseModel):
    project_id: str | None = None
    pattern_id: str
    pattern_name: str
    mermaid_code: str
    param_table: str = ""
    convergence_ratio: str
    design_points: list[str]
    talking_points: list[str] = Field(default_factory=list)
    render_tools: list[dict[str, str]]
    validation_issues: list[dict[str, Any]]
    compliance_notes: str
    data_disclaimer: str
    compliance_statement: str = ""
    compliance_checklist: list[str] = Field(default_factory=list)
    model_warnings: list[str] = Field(default_factory=list)
    figure_caption: str
    speaker_notes: str
    export_mode: str
    export_hints: dict[str, Any] = Field(default_factory=dict)
    render_guide: dict[str, Any] = Field(default_factory=dict)
    svg_wrapper: str | None = None


class PatternListResponse(BaseModel):
    patterns: list[dict[str, Any]]
