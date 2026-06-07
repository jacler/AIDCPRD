import { create } from "zustand";

import type { ExtractedRequirements } from "@/lib/api/consultation";
import { applyConsultationPlan } from "@/lib/api/consultation";
import {
  calculateCost,
  generateTopology,
  getProject,
  updateProject,
  updateTopology,
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
  isSavingTopology: boolean;
  topologyEditMode: boolean;
  error: string | null;

  setProject: (project: Project) => void;
  setParams: (params: Partial<DesignerParams>) => void;
  applyExtractedRequirements: (extracted: ExtractedRequirements) => void;
  applyExtractedAndGenerateTopology: (extracted: ExtractedRequirements) => Promise<void>;
  setTopologyEditMode: (enabled: boolean) => void;
  updateTopologyCounts: (partial: {
    servers?: number;
    gpus?: number;
    leaf_switches?: number;
    spine_switches?: number;
    storage_nodes?: number;
  }) => void;
  loadProject: (projectId: string) => Promise<void>;
  saveProject: () => Promise<void>;
  runGenerateTopology: () => Promise<void>;
  saveTopologyManual: (graphLayout?: {
    nodes: { id: string; position: { x: number; y: number } }[];
    edges: { id: string; source: string; target: string }[];
  }) => Promise<void>;
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
  isSavingTopology: false,
  topologyEditMode: false,
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

  applyExtractedRequirements: (extracted) => {
    const partial: Partial<DesignerParams> = {};
    if (extracted.target_gpus) partial.target_gpus = extracted.target_gpus;
    if (extracted.scenario) partial.scenario = extracted.scenario;
    if (extracted.gpus_per_node) partial.gpus_per_node = extracted.gpus_per_node;
    if (extracted.switch_ports) partial.switch_ports = extracted.switch_ports;
    if (extracted.network_arch) partial.network_arch = extracted.network_arch as DesignerParams["network_arch"];
    if (extracted.free_scheduler_with_server != null) {
      partial.free_scheduler_with_server = extracted.free_scheduler_with_server;
    }
    set({ params: { ...get().params, ...partial } });
    const project = get().project;
    if (project && extracted.project_name) {
      set({ project: { ...project, name: extracted.project_name } });
    }
  },

  applyExtractedAndGenerateTopology: async (extracted) => {
    const project = get().project;
    if (!project) return;

    set({ isGenerating: true, error: null });
    try {
      const result = await applyConsultationPlan({
        extracted,
        project_id: project.id,
        requirement_text: extracted.scheme_summary ?? extracted.description ?? undefined,
      });

      get().applyExtractedRequirements(extracted);

      const topologyResult = result.topology_result;
      if (topologyResult) {
        const bom: PreliminaryBOMItem[] = topologyResult.bom.map((item) => ({
          sku_id: item.sku_id,
          category: item.category,
          model: item.model,
          quantity: item.quantity,
          unit_price: Number(item.unit_price),
          total_price: Number(item.total_price),
          cost_dimension: item.cost_dimension as PreliminaryBOMItem["cost_dimension"],
        }));
        const topology: GenerateTopologyResponse = {
          compute: topologyResult.compute,
          network: topologyResult.network,
          storage: topologyResult.storage,
          bom,
          topology: topologyResult.topology,
        };
        set({
          project: {
            ...project,
            name: result.project_name,
            target_gpus: extracted.target_gpus ?? project.target_gpus,
            scenario: extracted.scenario ?? project.scenario,
          },
          topology,
          bom,
          isGenerating: false,
        });
      } else {
        await get().runGenerateTopology();
      }
    } catch (err) {
      set({
        isGenerating: false,
        error: err instanceof Error ? err.message : "应用方案失败",
      });
      throw err;
    }
  },

  setTopologyEditMode: (enabled) => set({ topologyEditMode: enabled }),

  updateTopologyCounts: (partial) => {
    const topology = get().topology;
    if (!topology) return;
    set({
      topology: {
        ...topology,
        compute: {
          servers: partial.servers ?? topology.compute.servers,
          gpus: partial.gpus ?? topology.compute.gpus,
        },
        network: {
          ...topology.network,
          leaf_switches: partial.leaf_switches ?? topology.network.leaf_switches,
          spine_switches: partial.spine_switches ?? topology.network.spine_switches,
        },
        storage: {
          nodes: partial.storage_nodes ?? topology.storage.nodes,
        },
      },
    });
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

  saveTopologyManual: async (graphLayout) => {
    const { project, topology, params } = get();
    if (!project || !topology) return;

    set({ isSavingTopology: true, error: null });
    try {
      const result = await updateTopology(project.id, {
        compute: topology.compute,
        network: topology.network,
        storage: topology.storage,
        graph_layout: graphLayout,
        scenario: params.scenario,
      });
      set({
        topology: result,
        bom: result.bom.map((item) => ({
          ...item,
          unit_price: Number(item.unit_price),
          total_price: Number(item.total_price),
        })),
        isSavingTopology: false,
        topologyEditMode: false,
      });
    } catch (err) {
      set({
        isSavingTopology: false,
        error: err instanceof Error ? err.message : "拓扑保存失败",
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
      isSavingTopology: false,
      topologyEditMode: false,
      error: null,
    });
  },
}));
