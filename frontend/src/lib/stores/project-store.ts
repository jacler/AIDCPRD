import { create } from "zustand";

import {
  calculateCost,
  generateTopology,
  getProject,
  updateProject,
} from "@/lib/api/projects";
import type {
  CalculateCostResponse,
  DesignerParams,
  GenerateTopologyResponse,
  PreliminaryBOMItem,
  Project,
  ProjectBOM,
} from "@/types";

interface ProjectStore {
  project: Project | null;
  params: DesignerParams;
  topology: GenerateTopologyResponse | null;
  bom: PreliminaryBOMItem[];
  savedBom: ProjectBOM[];
  costBreakdown: CalculateCostResponse["cost_breakdown"] | null;
  isGenerating: boolean;
  isCalculating: boolean;
  isSaving: boolean;
  error: string | null;

  setProject: (project: Project) => void;
  setParams: (params: Partial<DesignerParams>) => void;
  loadProject: (projectId: string) => Promise<void>;
  saveProject: () => Promise<void>;
  runGenerateTopology: () => Promise<void>;
  runCalculateCost: () => Promise<void>;
  updateBomQuantity: (index: number, quantity: number) => void;
  reset: () => void;
}

const defaultParams: DesignerParams = {
  target_gpus: 512,
  scenario: "TRAINING",
  gpus_per_node: 8,
  switch_ports: 64,
  network_arch: "FAT_TREE",
  free_scheduler_with_server: true,
};

export const useProjectStore = create<ProjectStore>((set, get) => ({
  project: null,
  params: { ...defaultParams },
  topology: null,
  bom: [],
  savedBom: [],
  costBreakdown: null,
  isGenerating: false,
  isCalculating: false,
  isSaving: false,
  error: null,

  setProject: (project) => {
    set({
      project,
      params: {
        ...get().params,
        target_gpus: project.target_gpus,
        scenario: project.scenario,
      },
    });
  },

  setParams: (partial) => {
    set({ params: { ...get().params, ...partial } });
  },

  loadProject: async (projectId) => {
    set({ error: null });
    try {
      const detail = await getProject(projectId);
      set({
        project: detail,
        params: {
          ...get().params,
          target_gpus: detail.target_gpus,
          scenario: detail.scenario,
        },
        topology: detail.topology_json
          ? ({
              compute: (detail.topology_json as Record<string, unknown>).compute,
              network: (detail.topology_json as Record<string, unknown>).network,
              storage: (detail.topology_json as Record<string, unknown>).storage,
              bom: [],
              topology: detail.topology_json,
            } as GenerateTopologyResponse)
          : null,
        savedBom: detail.bom,
        bom: detail.bom.map((row) => ({
          sku_id: row.sku_id,
          category: row.sku?.category ?? row.cost_dimension,
          model: row.sku?.model ?? "—",
          quantity: row.quantity,
          unit_price: Number(row.unit_price),
          total_price: Number(row.total_price),
          cost_dimension: row.cost_dimension,
        })),
        costBreakdown: detail.cost_breakdown_json
          ? (() => {
              const cb = detail.cost_breakdown_json as Record<string, number>;
              const total =
                Number(cb.COMPUTE ?? 0) +
                Number(cb.NETWORK ?? 0) +
                Number(cb.STORAGE ?? 0) +
                Number(cb.SOFTWARE ?? 0) +
                Number(cb.INFRA ?? 0);
              return {
                COMPUTE: Number(cb.COMPUTE ?? 0),
                NETWORK: Number(cb.NETWORK ?? 0),
                STORAGE: Number(cb.STORAGE ?? 0),
                SOFTWARE: Number(cb.SOFTWARE ?? 0),
                INFRA: Number(cb.INFRA ?? 0),
                total,
              };
            })()
          : null,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "加载项目失败",
      });
    }
  },

  saveProject: async () => {
    const { project, params } = get();
    if (!project) return;

    set({ isSaving: true, error: null });
    try {
      const updated = await updateProject(project.id, {
        name: project.name,
        target_gpus: params.target_gpus,
        scenario: params.scenario,
      });
      set({ project: updated, isSaving: false });
    } catch (err) {
      set({
        isSaving: false,
        error: err instanceof Error ? err.message : "保存失败",
      });
    }
  },

  runGenerateTopology: async () => {
    const { project, params } = get();
    if (!project) return;

    set({ isGenerating: true, error: null });
    try {
      const result = await generateTopology({
        target_gpus: params.target_gpus,
        scenario: params.scenario,
        network_arch: params.network_arch,
        gpus_per_node: params.gpus_per_node,
        switch_ports: params.switch_ports,
        project_id: project.id,
      });
      set({
        topology: result,
        bom: result.bom.map((item) => ({
          ...item,
          unit_price: Number(item.unit_price),
          total_price: Number(item.total_price),
        })),
        isGenerating: false,
      });
    } catch (err) {
      set({
        isGenerating: false,
        error: err instanceof Error ? err.message : "拓扑生成失败",
      });
    }
  },

  runCalculateCost: async () => {
    const { project, bom, params } = get();
    if (!project) return;

    const bomItems = bom
      .filter((item) => item.sku_id)
      .map((item) => ({
        sku_id: item.sku_id as string,
        quantity: item.quantity,
      }));

    if (bomItems.length === 0) {
      set({ error: "BOM 中缺少 SKU，请先导入 SKU 目录并重新生成拓扑" });
      return;
    }

    set({ isCalculating: true, error: null });
    try {
      const result = await calculateCost(project.id, {
        bom_items: bomItems,
        pricing_rules: {
          free_scheduler_with_server: params.free_scheduler_with_server,
        },
      });
      set({
        costBreakdown: result.cost_breakdown,
        savedBom: result.bom,
        isCalculating: false,
        project: project
          ? { ...project, status: "COMPLETED" }
          : null,
      });
    } catch (err) {
      set({
        isCalculating: false,
        error: err instanceof Error ? err.message : "成本计算失败",
      });
    }
  },

  updateBomQuantity: (index, quantity) => {
    const bom = [...get().bom];
    if (!bom[index] || quantity <= 0) return;
    bom[index] = {
      ...bom[index],
      quantity,
      total_price: bom[index].unit_price * quantity,
    };
    set({ bom });
  },

  reset: () => {
    set({
      project: null,
      params: { ...defaultParams },
      topology: null,
      bom: [],
      savedBom: [],
      costBreakdown: null,
      isGenerating: false,
      isCalculating: false,
      isSaving: false,
      error: null,
    });
  },
}));
