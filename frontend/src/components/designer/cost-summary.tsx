"use client";

import { Calculator, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  formatCurrencyFull,
  formatNumber,
  formatPercent,
} from "@/lib/format";
import { useProjectStore } from "@/lib/stores/project-store";
import { COST_DIMENSION_LABELS, type CostBreakdown, type CostDimension } from "@/types";

const DIMENSIONS: CostDimension[] = [
  "COMPUTE",
  "NETWORK",
  "STORAGE",
  "SOFTWARE",
  "INFRA",
];

const BAR_COLORS: Record<CostDimension, string> = {
  COMPUTE: "bg-emerald-500",
  NETWORK: "bg-sky-500",
  STORAGE: "bg-violet-500",
  SOFTWARE: "bg-amber-500",
  INFRA: "bg-primary",
};

function CostBreakdownBars({ breakdown }: { breakdown: CostBreakdown }) {
  return (
    <div className="space-y-3">
      <div className="text-right">
        <span className="text-2xl font-bold text-primary">
          {formatCurrencyFull(breakdown.total)}
        </span>
      </div>
      {DIMENSIONS.map((dim) => {
        const value = breakdown[dim];
        const pct = formatPercent(value, breakdown.total);
        const width = breakdown.total > 0 ? (value / breakdown.total) * 100 : 0;
        return (
          <div key={dim} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">
                {COST_DIMENSION_LABELS[dim]}
              </span>
              <span>
                {formatNumber(value)}{" "}
                <span className="text-muted-foreground">({pct})</span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full transition-all ${BAR_COLORS[dim]}`}
                style={{ width: `${Math.max(width, value > 0 ? 2 : 0)}%` }}
              />
            </div>
          </div>
        );
      })}
      <p className="text-[10px] text-muted-foreground leading-relaxed pt-1">
        * 以上成本为估算值，实际落地价格受商务条款、供应链及实施范围影响，仅供参考。
      </p>
    </div>
  );
}

export function CostSummary() {
  const costBreakdown = useProjectStore((s) => s.costBreakdown);
  const runCalculateCost = useProjectStore((s) => s.runCalculateCost);
  const isCalculating = useProjectStore((s) => s.isCalculating);
  const bom = useProjectStore((s) => s.bom);
  const bomSubtotal = bom.reduce((s, i) => s + i.total_price, 0);

  return (
    <div className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">成本拆解</h2>
        <Button
          size="sm"
          variant={costBreakdown ? "outline" : "default"}
          onClick={runCalculateCost}
          disabled={isCalculating || bom.length === 0}
        >
          {isCalculating ? (
            <Loader2 className="animate-spin h-4 w-4" />
          ) : (
            <Calculator className="h-4 w-4" />
          )}
          计算成本
        </Button>
      </div>

      {costBreakdown ? (
        <CostBreakdownBars breakdown={costBreakdown} />
      ) : (
        <div className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
          <p>BOM 预估: {formatCurrencyFull(bomSubtotal)}</p>
          <p className="mt-1 text-xs">点击「计算成本」生成 5 维拆解</p>
        </div>
      )}
    </div>
  );
}
