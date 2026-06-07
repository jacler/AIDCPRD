import { apiFetch } from "@/lib/api-client";

export interface DiagramGeneratePayload {
  requirement?: string;
  pattern_id?: string;
  target_gpus?: number;
  scenario?: string;
  export_mode?: "ppt_ready" | "doc_embed" | "web_interactive";
  liquid_cooling?: boolean;
  domestic_mode?: boolean;
  figure_no?: string;
}

export interface DiagramGenerateResponse {
  project_id?: string | null;
  pattern_id: string;
  pattern_name: string;
  mermaid_code: string;
  param_table: string;
  convergence_ratio: string;
  design_points: string[];
  talking_points: string[];
  render_tools: Array<{ name: string; url?: string; export: string }>;
  validation_issues: Array<{ rule_id?: string; message: string; fix_snippet?: string }>;
  compliance_notes: string;
  data_disclaimer: string;
  compliance_statement: string;
  compliance_checklist: string[];
  model_warnings: string[];
  figure_caption: string;
  speaker_notes: string;
  export_mode: string;
  export_hints: Record<string, unknown>;
  render_guide?: Record<string, unknown>;
}

export async function generateProjectDiagram(projectId: string, payload: DiagramGeneratePayload = {}) {
  return apiFetch<DiagramGenerateResponse>(`/api/v1/diagrams/projects/${projectId}/generate`, {
    method: "POST",
    body: JSON.stringify({ export_mode: "ppt_ready", ...payload }),
  });
}

export async function matchDiagramPattern(requirement: string, targetGpus?: number) {
  return apiFetch<{ pattern_id: string; display_name: string; use_case: string }>(
    "/api/v1/diagrams/match",
    {
      method: "POST",
      body: JSON.stringify({ requirement, target_gpus: targetGpus }),
    }
  );
}
