"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getMultiPlan, type PlanTradeOffItem } from "@/lib/api/multi-plan";
import { formatCurrency } from "@/lib/format";

const PLAN_LABELS: Record<string, string> = {
  performance_optimized: "性能优先",
  balanced: "均衡方案",
  cost_optimized: "性价比优先",
};

interface TradeOffMatrixProps {
  projectId: string;
}

export function TradeOffMatrix({ projectId }: TradeOffMatrixProps) {
  const [electricityPrice, setElectricityPrice] = useState(0.8);

  const { data, isLoading, error } = useQuery({
    queryKey: ["multi-plan", projectId, electricityPrice],
    queryFn: () =>
      getMultiPlan(projectId, { electricity_price: electricityPrice }),
  });

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-base">方案权衡矩阵</CardTitle>
        <CardDescription>
          三档架构路线 · 5 年 TCO · 隐性代价标注
        </CardDescription>
        <div className="mt-3 flex max-w-xs items-end gap-3">
          <div className="flex-1 space-y-1">
            <Label htmlFor="elec-price" className="text-xs">
              当地电价（元/kWh）
            </Label>
            <Input
              id="elec-price"
              type="number"
              min={0.1}
              max={5}
              step={0.05}
              value={electricityPrice}
              onChange={(e) =>
                setElectricityPrice(Number(e.target.value) || 0.8)
              }
            />
          </div>
          <p className="pb-2 text-[10px] text-muted-foreground">
            调整后 TCO 实时重算
          </p>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : "加载失败"}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>方案</TableHead>
                  <TableHead>定位</TableHead>
                  <TableHead>收敛比</TableHead>
                  <TableHead className="text-right">硬件 CAPEX</TableHead>
                  <TableHead className="text-right">5 年 TCO</TableHead>
                  <TableHead>隐性代价</TableHead>
                  <TableHead>失效边界</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.plans ?? []).map((plan) => (
                  <PlanRow key={plan.plan_id} plan={plan} />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PlanRow({ plan }: { plan: PlanTradeOffItem }) {
  return (
    <TableRow className={plan.recommended ? "bg-primary/5" : undefined}>
      <TableCell className="font-medium whitespace-nowrap">
        {PLAN_LABELS[plan.plan_id] ?? plan.plan_id}
        {plan.recommended && (
          <span className="ml-1 text-[10px] text-primary">推荐</span>
        )}
      </TableCell>
      <TableCell className="max-w-[200px] text-xs text-muted-foreground">
        {plan.headline}
      </TableCell>
      <TableCell className="text-xs whitespace-nowrap">
        {plan.convergence_ratio}
        <br />
        <span className="text-muted-foreground">{plan.network_technology}</span>
      </TableCell>
      <TableCell className="text-right tabular-nums text-sm">
        {formatCurrency(plan.hardware_capex)}
      </TableCell>
      <TableCell className="text-right tabular-nums text-sm font-semibold">
        {formatCurrency(plan.tco_5y)}
        <div className="text-[10px] font-normal text-muted-foreground">
          电费敏感度 {plan.tco_sensitivity.impact_pct}%
        </div>
      </TableCell>
      <TableCell className="max-w-[220px] text-xs">
        {plan.trade_offs.map((t, i) => (
          <p key={i} className="mb-1 flex gap-1 text-amber-800">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600" />
            <span>{t}</span>
          </p>
        ))}
      </TableCell>
      <TableCell className="max-w-[180px] text-xs text-muted-foreground">
        {plan.failure_boundary}
      </TableCell>
    </TableRow>
  );
}
