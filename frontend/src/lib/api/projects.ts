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

export interface UpdateTopologyPayload {
  compute?: { servers: number; gpus: number };
  network?: {
    leaf_switches: number;
    spine_switches: number;
    rdma_nics: number;
    dac_cables: number;
    optics_400g: number;
  };
  storage?: { nodes: number };
  graph_layout?: {
    nodes: { id: string; position: { x: number; y: number } }[];
    edges?: { id: string; source: string; target: string }[];
  };
  scenario?: ProjectScenario;
}

export async function updateTopology(projectId: string, payload: UpdateTopologyPayload) {
  return apiFetch<GenerateTopologyResponse>(`/api/v1/projects/${projectId}/topology`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
