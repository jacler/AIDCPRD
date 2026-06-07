import { apiFetch } from "@/lib/api-client";

export interface PlanTradeOffItem {
  plan_id: string;
  headline: string;
  trade_offs: string[];
  failure_boundary: string;
  tco_sensitivity: {
    variable: string;
    impact_pct: number;
    baseline_price_cny_per_kwh?: number;
    tco_at_minus_25pct?: number;
    tco_at_plus_25pct?: number;
  };
  convergence_ratio: string;
  network_technology: string;
  mfu_relative: number;
  cost_breakdown: Record<string, number>;
  hardware_capex: number;
  tco_5y: number;
  tco_breakdown: Record<string, number>;
  recommended: boolean;
}

export interface MultiPlanResponse {
  project_id: string;
  electricity_price_cny_per_kwh: number;
  pue: number;
  plans: PlanTradeOffItem[];
}

export async function getMultiPlan(
  projectId: string,
  params?: { electricity_price?: number; pue?: number }
) {
  const qs = new URLSearchParams();
  if (params?.electricity_price != null) {
    qs.set("electricity_price", String(params.electricity_price));
  }
  if (params?.pue != null) {
    qs.set("pue", String(params.pue));
  }
  const query = qs.toString();
  return apiFetch<MultiPlanResponse>(
    `/api/v1/projects/${projectId}/multi-plan${query ? `?${query}` : ""}`
  );
}
