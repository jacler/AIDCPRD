from typing import Any

from pydantic import BaseModel, Field


class VisualizationResponse(BaseModel):
    project_id: str
    convergence_ratio: str
    compute_network_svg: str
    storage_network_svg: str
    cabinet_layout_svg: str
    cabinet_warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TechnicalProposalMeta(BaseModel):
    project_id: str
    filename: str
    sections: list[str] = Field(default_factory=list)
    disclaimer: str
