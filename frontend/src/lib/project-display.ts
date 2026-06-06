import type { Project, ProjectScenario, ProjectStatus } from "@/types";

export function projectCostTotal(project: Project): number {
  if (!project.cost_breakdown_json) return 0;
  const cb = project.cost_breakdown_json as Record<string, number>;
  return (
    Number(cb.COMPUTE ?? 0) +
    Number(cb.NETWORK ?? 0) +
    Number(cb.STORAGE ?? 0) +
    Number(cb.SOFTWARE ?? 0) +
    Number(cb.INFRA ?? 0)
  );
}

export function getScenarioStyle(scenario: ProjectScenario): string {
  switch (scenario) {
    case "TRAINING":
      return "bg-blue-100 text-blue-800";
    case "INFERENCE":
      return "bg-emerald-100 text-emerald-800";
    default:
      return "bg-amber-100 text-amber-800";
  }
}

export function getDisplayStatus(project: Project): {
  label: string;
  className: string;
} {
  if (project.status === "COMPLETED") {
    return { label: "已完成", className: "text-emerald-600" };
  }
  if (project.topology_json) {
    return { label: "设计中", className: "text-blue-600" };
  }
  if (project.status === "CALCULATING") {
    return { label: "计算中", className: "text-blue-600" };
  }
  return { label: "草稿", className: "text-amber-600" };
}

export function statusBadgeStyle(status: ProjectStatus, hasTopology: boolean): string {
  if (status === "COMPLETED") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (hasTopology || status === "CALCULATING")
    return "bg-blue-50 text-blue-700 border-blue-200";
  return "bg-amber-50 text-amber-700 border-amber-200";
}
