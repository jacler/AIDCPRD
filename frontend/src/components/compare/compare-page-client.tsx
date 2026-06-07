"use client";

import Link from "next/link";

import { CompliancePanel } from "@/components/compare/compliance-panel";
import { TradeOffMatrix } from "@/components/compare/trade-off-matrix";
import { CostWaterfall } from "@/components/CostWaterfall";
import { RadarCompare } from "@/components/RadarCompare";
import { MainNav } from "@/components/layout/main-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useProjectStore } from "@/lib/stores/project-store";
import { formatCurrency } from "@/lib/format";
import { useEffect } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";

interface ComparePageClientProps {
  projectId: string;
}

export function ComparePageClient({ projectId }: ComparePageClientProps) {
  const project = useProjectStore((s) => s.project);
  const costBreakdown = useProjectStore((s) => s.costBreakdown);
  const loadProject = useProjectStore((s) => s.loadProject);
  const reset = useProjectStore((s) => s.reset);

  useEffect(() => {
    void loadProject(projectId);
    return () => reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  if (!project) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const ibTotal = costBreakdown?.total ?? 0;
  const roceTotal = ibTotal * 0.88;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav showNewProject={false} />

      <div className="mx-auto max-w-[1200px] px-6 py-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <Badge variant="secondary">方案 PK</Badge>
              <span className="text-sm text-muted-foreground">{project.target_gpus} GPU</span>
            </div>
            <h1 className="text-xl font-bold">{project.name}</h1>
            <p className="text-sm text-muted-foreground">
              三档方案权衡 · 5 年 TCO · 5 维雷达对比
            </p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link
              href={`/projects/${projectId}/designer`}
              className="inline-flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>返回设计器</span>
            </Link>
          </Button>
        </div>

        <TradeOffMatrix projectId={projectId} />

        <div className="mt-6">
          <CompliancePanel projectId={projectId} />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Card className="border-blue-200/60 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">全 IB 方案</CardTitle>
                <Badge className="bg-blue-600 hover:bg-blue-600">推荐</Badge>
              </div>
              <CardDescription>InfiniBand · 低延迟 · 高 MFU</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>目标规模: {project.target_gpus} GPU</p>
              {costBreakdown ? (
                <p className="text-2xl font-bold text-foreground">
                  {formatCurrency(ibTotal)}
                </p>
              ) : (
                <p className="text-sm italic">请先在设计器完成成本计算</p>
              )}
              <ul className="list-disc space-y-1 pl-4">
                <li>算力效率 (MFU) 领先 RoCE 约 15%</li>
                <li>无收敛 Fat-Tree 扩展至千卡规模</li>
                <li>单卡 TCO 较高，IB 交换机溢价明显</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">RoCE 方案</CardTitle>
              <CardDescription>Ethernet RDMA · 成本友好</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>目标规模: {project.target_gpus} GPU</p>
              {costBreakdown ? (
                <p className="text-2xl font-bold text-emerald-600">
                  {formatCurrency(roceTotal)}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    (-12%)
                  </span>
                </p>
              ) : (
                <p className="text-sm italic">请先在设计器完成成本计算</p>
              )}
              <ul className="list-disc space-y-1 pl-4">
                <li>单卡成本更低，供应链选择更广</li>
                <li>以太网生态成熟，运维门槛低</li>
                <li>大规模训练 MFU 略低于 IB</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">5 维雷达对比</CardTitle>
              <CardDescription>
                单卡成本 · 算力效率 · 供应链 · 扩展性 · 能耗 (PUE)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mx-auto max-w-xl">
                <RadarCompare
                  breakdown={costBreakdown}
                  targetGpus={project.target_gpus}
                  embedded
                />
              </div>
            </CardContent>
          </Card>

          {costBreakdown && (
            <Card className="lg:col-span-2 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base">当前方案成本瀑布</CardTitle>
                <CardDescription>基于 IB 方案的 5 维拆解</CardDescription>
              </CardHeader>
              <CardContent>
                <CostWaterfall breakdown={costBreakdown} embedded />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
