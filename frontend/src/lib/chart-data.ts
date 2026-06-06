import type { CostBreakdown, WaterfallData } from "@/types";
import { COST_DIMENSION_LABELS, type CostDimension } from "@/types";

const DIMENSIONS: CostDimension[] = [
  "COMPUTE",
  "NETWORK",
  "STORAGE",
  "SOFTWARE",
  "INFRA",
];

export interface WaterfallChartRow {
  name: string;
  base: number;
  value: number;
  total: number;
  isTotal?: boolean;
}

export function buildWaterfallChartData(
  breakdown: CostBreakdown
): WaterfallChartRow[] {
  let running = 0;
  const rows: WaterfallChartRow[] = DIMENSIONS.map((dim) => {
    const value = breakdown[dim];
    const base = running;
    running += value;
    return {
      name: COST_DIMENSION_LABELS[dim],
      base,
      value,
      total: running,
    };
  });

  rows.push({
    name: "落地总价",
    base: 0,
    value: breakdown.total,
    total: breakdown.total,
    isTotal: true,
  });

  return rows;
}

export function buildWaterfallData(breakdown: CostBreakdown): WaterfallData[] {
  let running = 0;
  return DIMENSIONS.map((dim) => {
    const value = breakdown[dim];
    running += value;
    return {
      name: COST_DIMENSION_LABELS[dim],
      value,
      total: running,
    };
  });
}

export interface RadarDimension {
  dimension: string;
  ib: number;
  roce: number;
  fullMark: number;
}

/** Heuristic scores for IB vs RoCE scheme comparison (0–100). */
export function buildRadarCompareData(
  breakdown: CostBreakdown | null,
  targetGpus: number
): RadarDimension[] {
  const total = breakdown?.total ?? targetGpus * 280_000;
  const perGpuCost = total / Math.max(targetGpus, 1);

  // Lower per-GPU cost → higher score (inverted normalization)
  const costScoreIb = Math.max(20, Math.min(95, 100 - (perGpuCost / 400_000) * 40));
  const costScoreRoce = Math.min(98, costScoreIb + 12);

  return [
    {
      dimension: "单卡成本",
      ib: Math.round(costScoreIb),
      roce: Math.round(costScoreRoce),
      fullMark: 100,
    },
    {
      dimension: "算力效率",
      ib: 92,
      roce: 78,
      fullMark: 100,
    },
    {
      dimension: "供应链",
      ib: 75,
      roce: 88,
      fullMark: 100,
    },
    {
      dimension: "扩展性",
      ib: 90,
      roce: 82,
      fullMark: 100,
    },
    {
      dimension: "能耗 PUE",
      ib: 85,
      roce: 83,
      fullMark: 100,
    },
  ];
}
