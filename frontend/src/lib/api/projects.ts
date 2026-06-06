import { apiFetch } from "@/lib/api-client";
import type {
  CalculateCostResponse,
  GenerateTopologyResponse,
  PaginatedResponse,
  Project,
  ProjectDetail,
  ProjectScenario,
} from "@/types";

export interface CreateProjectPayload {
  name: string;
  target_gpus: number;
  scenario: ProjectScenario;
  description?: string;
}

export interface GenerateTopologyPayload {
  target_gpus: number;
  scenario: ProjectScenario;
  network_arch?: "FAT_TREE";
  gpus_per_node?: number;
  switch_ports?: number;
  project_id?: string;
}

export interface CalculateCostPayload {
  bom_items: { sku_id: string; quantity: number }[];
  pricing_rules?: Record<string, unknown>;
}

export async function listProjects(page = 1, pageSize = 20) {
  return apiFetch<PaginatedResponse<Project>>(
    `/api/v1/projects?page=${page}&page_size=${pageSize}`
  );
}

export async function createProject(payload: CreateProjectPayload) {
  return apiFetch<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getProject(projectId: string) {
  return apiFetch<ProjectDetail>(`/api/v1/projects/${projectId}`);
}

export async function updateProject(
  projectId: string,
  payload: {
    name?: string;
    target_gpus?: number;
    scenario?: ProjectScenario;
    description?: string;
  }
) {
  return apiFetch<Project>(`/api/v1/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function generateTopology(payload: GenerateTopologyPayload) {
  return apiFetch<GenerateTopologyResponse>(
    "/api/v1/projects/generate-topology",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function calculateCost(
  projectId: string,
  payload: CalculateCostPayload
) {
  return apiFetch<CalculateCostResponse>(
    `/api/v1/projects/${projectId}/calculate-cost`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}
