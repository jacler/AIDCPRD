"use client";

import Link from "next/link";
import { BarChart3, Expand } from "lucide-react";

import { CostWaterfall } from "@/components/CostWaterfall";
import { BOMTable } from "@/components/designer/bom-table";
import { CostSummary } from "@/components/designer/cost-summary";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useProjectStore } from "@/lib/stores/project-store";

interface DesignerRightPanelProps {
  projectId: string;
}

export function DesignerRightPanel({ projectId }: DesignerRightPanelProps) {
  const costBreakdown = useProjectStore((s) => s.costBreakdown);

  return (
    <aside className="flex w-[440px] shrink-0 flex-col overflow-y-auto border-l bg-background">
      <BOMTable />
      <Separator />
      <CostSummary />
      {costBreakdown && (
        <>
          <Separator />
          <div className="p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <BarChart3 className="h-4 w-4 text-primary" />
              成本瀑布
            </div>
            <CostWaterfall breakdown={costBreakdown} embedded />
          </div>
        </>
      )}
      <Separator />
      <div className="flex items-center justify-between p-4 text-xs text-muted-foreground">
        <Link href="/" className="text-primary hover:underline">
          ← 返回项目列表
        </Link>
        <Button variant="ghost" size="sm" className="h-7 text-xs" asChild>
          <Link href={`/projects/${projectId}/compare`}>
            <Expand className="h-3 w-3" />
            方案 PK
          </Link>
        </Button>
      </div>
    </aside>
  );
}
