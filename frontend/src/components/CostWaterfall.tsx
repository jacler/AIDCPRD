"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { buildWaterfallChartData } from "@/lib/chart-data";
import { formatCurrency } from "@/lib/format";
import type { CostBreakdown } from "@/types";

const INCREMENT_COLOR = "hsl(142 71% 45%)";
const TOTAL_COLOR = "hsl(221 83% 53%)";

interface CostWaterfallProps {
  breakdown: CostBreakdown | null;
  embedded?: boolean;
}

function WaterfallTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { name: string; value: number; total: number } }>;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-lg border bg-background px-3 py-2 text-xs shadow-md">
      <p className="font-medium">{row.name}</p>
      <p className="text-muted-foreground">
        增量: {formatCurrency(row.value)}
      </p>
      {!row.name.includes("总价") && (
        <p className="text-primary">累计: {formatCurrency(row.total)}</p>
      )}
    </div>
  );
}

export function CostWaterfall({ breakdown, embedded = false }: CostWaterfallProps) {
  const chart = !breakdown ? (
    <div className="flex h-48 items-center justify-center rounded-md border border-dashed text-xs text-muted-foreground">
      暂无数据
    </div>
  ) : (
    (() => {
      const data = buildWaterfallChartData(breakdown);
      return (
        <>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={52}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) =>
                  v >= 100_000_000
                    ? `${(v / 100_000_000).toFixed(1)}亿`
                    : v >= 10_000
                      ? `${(v / 10_000).toFixed(0)}万`
                      : String(v)
                }
                width={44}
              />
              <Tooltip content={<WaterfallTooltip />} cursor={{ fill: "hsl(var(--muted)/0.4)" }} />
              <Bar dataKey="base" stackId="waterfall" fill="transparent" radius={0} />
              <Bar dataKey="value" stackId="waterfall" radius={[4, 4, 0, 0]} maxBarSize={48}>
                {data.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={entry.isTotal ? TOTAL_COLOR : INCREMENT_COLOR}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-2 flex justify-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: INCREMENT_COLOR }}
              />
              维度增量
            </span>
            <span className="flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: TOTAL_COLOR }}
              />
              落地总价
            </span>
          </div>
        </>
      );
    })()
  );

  if (embedded) return chart;

  if (!breakdown) {
    return (
      <Card className="border-0 shadow-none rounded-none">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">成本瀑布图</CardTitle>
          <CardDescription>计算成本后展示 5 维累加过程</CardDescription>
        </CardHeader>
        <CardContent>{chart}</CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-none rounded-none">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">成本瀑布图</CardTitle>
        <CardDescription>硬件 → 软件 → 基建 → 落地总价</CardDescription>
      </CardHeader>
      <CardContent className="pb-2">{chart}</CardContent>
    </Card>
  );
}
