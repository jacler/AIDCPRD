/** Enums — keep in sync with backend Pydantic schemas */

export type SKUCategory =
  | "GPU"
  | "CPU"
  | "MEM"
  | "SWITCH"
  | "OPTIC"
  | "STORAGE"
  | "SOFTWARE"
  | "INFRA";

export type ProjectScenario = "TRAINING" | "INFERENCE" | "MIXED";

export type ProjectStatus = "DRAFT" | "CALCULATING" | "COMPLETED";

export type NetworkArch = "FAT_TREE";

export type CostDimension =
  | "COMPUTE"
  | "NETWORK"
  | "STORAGE"
  | "SOFTWARE"
  | "INFRA";

export type UserRole = "ADMIN" | "USER";

export interface UserAccount {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SKUCatalog {
  id: string;
  category: SKUCategory;
  vendor: string;
  model: string;
  specs_json: Record<string, unknown>;
  base_price: number;
  channel_price: number | null;
  cost_dimension: CostDimension;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  target_gpus: number;
  scenario: ProjectScenario;
  status: ProjectStatus;
  description?: string | null;
  topology_json?: Record<string, unknown> | null;
  cost_breakdown_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectBOM {
  id: string;
  project_id: string;
  sku_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  cost_dimension: CostDimension;
  sku?: SKUCatalog;
  created_at: string;
}

export interface PreliminaryBOMItem {
  sku_id: string | null;
  category: string;
  model: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  cost_dimension: CostDimension;
}

export interface TopologyCompute {
  servers: number;
  gpus: number;
}

export interface TopologyNetwork {
  leaf_switches: number;
  spine_switches: number;
  rdma_nics: number;
  dac_cables: number;
  optics_400g: number;
}

export interface TopologyStorage {
  nodes: number;
}

export interface GenerateTopologyResponse {
  compute: TopologyCompute;
  network: TopologyNetwork;
  storage: TopologyStorage;
  bom: PreliminaryBOMItem[];
  topology: Record<string, unknown>;
}

export interface CostBreakdown {
  COMPUTE: number;
  NETWORK: number;
  STORAGE: number;
  SOFTWARE: number;
  INFRA: number;
  total: number;
}

export interface CalculateCostResponse {
  project_id: string;
  cost_breakdown: CostBreakdown;
  bom: ProjectBOM[];
}

export interface ProjectDetail extends Project {
  bom: ProjectBOM[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DesignerParams {
  target_gpus: number;
  scenario: ProjectScenario;
  gpus_per_node: number;
  switch_ports: number;
  network_arch: NetworkArch;
  free_scheduler_with_server: boolean;
}

export interface WaterfallData {
  name: string;
  value: number;
  total: number;
}

export const COST_DIMENSION_LABELS: Record<CostDimension, string> = {
  COMPUTE: "计算硬件",
  NETWORK: "网络硬件",
  STORAGE: "存储",
  SOFTWARE: "软件授权",
  INFRA: "实施维保",
};

export const SCENARIO_LABELS: Record<ProjectScenario, string> = {
  TRAINING: "训练",
  INFERENCE: "推理",
  MIXED: "混合",
};

export const STATUS_LABELS: Record<ProjectStatus, string> = {
  DRAFT: "草稿",
  CALCULATING: "计算中",
  COMPLETED: "已完成",
};
