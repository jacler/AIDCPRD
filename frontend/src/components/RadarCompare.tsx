"use client";

import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { buildRadarCompareData } from "@/lib/chart-data";
import type { CostBreakdown } from "@/types";

const IB_COLOR = "hsl(221 83% 53%)";
const ROCE_COLOR = "hsl(142 71% 45%)";

interface RadarCompareProps {
  breakdown: CostBreakdown | null;
  targetGpus: number;
  embedded?: boolean;
}

function RadarTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-background px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
}

export function RadarCompare({
  breakdown,
  targetGpus,
  embedded = false,
}: RadarCompareProps) {
  const data = buildRadarCompareData(breakdown, targetGpus);

  const chart = (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
        <PolarGrid stroke="hsl(var(--border))" />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
        />
        <Radar
          name="全 IB"
          dataKey="ib"
          stroke={IB_COLOR}
          fill={IB_COLOR}
          fillOpacity={0.25}
          strokeWidth={2}
        />
        <Radar
          name="RoCE"
          dataKey="roce"
          stroke={ROCE_COLOR}
          fill={ROCE_COLOR}
          fillOpacity={0.2}
          strokeWidth={2}
        />
        <Tooltip content={<RadarTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" />
      </RadarChart>
    </ResponsiveContainer>
  );

  if (embedded) return chart;

  return (
    <Card className="border-0 shadow-none rounded-none">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">方案对比</CardTitle>
        <CardDescription>全 IB vs RoCE · 5 维优劣势</CardDescription>
      </CardHeader>
      <CardContent className="pb-4">{chart}</CardContent>
    </Card>
  );
}
