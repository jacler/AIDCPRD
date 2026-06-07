"use client";

import Link from "next/link";
import { BarChart3, Expand } from "lucide-react";

import { CostWaterfall } from "@/components/CostWaterfall";
import { ArchitectureDiagramPanel } from "@/components/designer/architecture-diagram-panel";
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
  const project = useProjectStore((s) => s.project);
  const topology = useProjectStore((s) => s.topology);

  return (
    <aside className="flex w-[440px] shrink-0 flex-col overflow-y-auto border-l bg-background">
      <BOMTable />
      <Separator />
      {topology && project && (
        <>
          <div className="p-4">
            <ArchitectureDiagramPanel
              projectId={projectId}
              projectName={project.name}
              targetGpus={project.target_gpus}
            />
          </div>
          <Separator />
        </>
      )}
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
          <Link
            href={`/projects/${projectId}/compare`}
            className="inline-flex items-center gap-1.5"
          >
            <Expand className="h-3 w-3" />
            <span>方案 PK</span>
          </Link>
        </Button>
      </div>
    </aside>
  );
}
