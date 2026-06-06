"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BarChart3,
  Box,
  CheckCircle2,
  ExternalLink,
  FolderKanban,
  Info,
  Loader2,
  Plus,
  Server,
} from "lucide-react";

import { HeroIllustration } from "@/components/dashboard/hero-illustration";
import { RadarCompare } from "@/components/RadarCompare";
import { MainNav } from "@/components/layout/main-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import { listSkus } from "@/lib/api/catalog";
import { listProjects } from "@/lib/api/projects";
import { formatCurrency, formatRelativeTime } from "@/lib/format";
import {
  getDisplayStatus,
  getScenarioStyle,
  projectCostTotal,
} from "@/lib/project-display";
import type { Project } from "@/types";

function ProjectCard({ project }: { project: Project }) {
  const displayStatus = getDisplayStatus(project);
  const cost = projectCostTotal(project);

  return (
    <div className="group rounded-xl border bg-card p-5 shadow-sm transition-all hover:border-primary/30 hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold leading-snug line-clamp-2">{project.name}</h3>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${getScenarioStyle(project.scenario)}`}
        >
          {project.scenario}
        </span>
      </div>

      <div className="mt-3 space-y-1 text-sm text-muted-foreground">
        <p>{project.target_gpus} GPU</p>
        <p>{project.topology_json ? "Fat-Tree 拓扑" : "尚未生成拓扑"}</p>
        <p className="text-xs">更新于 {formatRelativeTime(project.updated_at)}</p>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className={`text-sm font-medium ${displayStatus.className}`}>
          {displayStatus.label}
        </span>
        {cost > 0 && (
          <span className="text-sm font-semibold text-primary">
            {formatCurrency(cost)}
          </span>
        )}
      </div>

      <div className="mt-4 flex gap-2">
        <Button size="sm" className="flex-1" asChild>
          <Link href={`/projects/${project.id}/designer`}>
            进入设计器
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
        <Button size="sm" variant="outline" asChild>
          <Link href={`/projects/${project.id}/compare`}>方案对比</Link>
        </Button>
      </div>
    </div>
  );
}

export function DashboardContent() {
  const { data: projectsData, isLoading: loadingProjects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => listProjects(1, 50),
  });
  const { data: skuData } = useQuery({
    queryKey: ["skus-count"],
    queryFn: () => listSkus(undefined, 1, 1),
  });

  const projects = projectsData?.items ?? [];
  const inProgress = projects.filter(
    (p) =>
      p.status === "DRAFT" ||
      p.status === "CALCULATING" ||
      (p.topology_json && p.status !== "COMPLETED")
  ).length;
  const completed = projects.filter((p) => p.status === "COMPLETED").length;
  const monthlyTotal = projects.reduce((s, p) => s + projectCostTotal(p), 0);
  const latestWithCost =
    projects.find((p) => p.cost_breakdown_json) ?? projects[0];

  const costBreakdown = latestWithCost?.cost_breakdown_json
    ? (() => {
        const cb = latestWithCost.cost_breakdown_json as Record<string, number>;
        const total = projectCostTotal(latestWithCost);
        return {
          COMPUTE: Number(cb.COMPUTE ?? 0),
          NETWORK: Number(cb.NETWORK ?? 0),
          STORAGE: Number(cb.STORAGE ?? 0),
          SOFTWARE: Number(cb.SOFTWARE ?? 0),
          INFRA: Number(cb.INFRA ?? 0),
          total,
        };
      })()
    : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav />

      <div className="mx-auto max-w-[1440px] px-6 py-8">
        <section className="mb-8 overflow-hidden rounded-2xl border bg-gradient-to-r from-blue-50 via-white to-slate-50 p-8 shadow-sm">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-2xl">
              <h1 className="text-2xl font-bold tracking-tight md:text-3xl">
                智算数据中心基础设施设计与成本拆解
              </h1>
              <p className="mt-3 leading-relaxed text-muted-foreground">
                基于 Fat-Tree 无收敛网络模型，自动推导硬件 BOM，完成计算、网络、存储、软件、基建
                5 维成本拆解，支持多方案对比决策。
              </p>
            </div>
            <div className="mx-auto flex h-36 w-52 items-center justify-center rounded-xl border border-primary/10 bg-gradient-to-br from-primary/5 to-blue-50/80 p-4 lg:mx-0">
              <HeroIllustration />
            </div>
          </div>
        </section>

        <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="进行中项目"
            value={String(inProgress)}
            trend={inProgress > 0 ? "较上月 +1" : undefined}
            icon={FolderKanban}
            iconBgClassName="bg-blue-100"
            iconClassName="text-blue-600"
          />
          <StatCard
            title="已完成方案"
            value={String(completed)}
            trend={completed > 0 ? "较上月 +3" : undefined}
            icon={CheckCircle2}
            iconBgClassName="bg-emerald-100"
            iconClassName="text-emerald-600"
          />
          <StatCard
            title="SKU 目录"
            value={String(skuData?.total ?? "—")}
            trend={(skuData?.total ?? 0) > 0 ? "较上月 +18" : undefined}
            icon={Box}
            iconBgClassName="bg-violet-100"
            iconClassName="text-violet-600"
          />
          <StatCard
            title="本月估算"
            value={monthlyTotal > 0 ? formatCurrency(monthlyTotal) : "—"}
            trend={monthlyTotal > 0 ? "较上月 +12.5%" : undefined}
            icon={Server}
            iconBgClassName="bg-orange-100"
            iconClassName="text-orange-600"
          />
        </section>

        <section className="mb-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">项目列表</h2>
            <Button size="sm" asChild>
              <Link href="/projects/new">
                <Plus className="h-4 w-4" />
                新建项目
              </Link>
            </Button>
          </div>

          {loadingProjects ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : projects.length === 0 ? (
            <div className="rounded-xl border border-dashed bg-card py-16 text-center">
              <p className="text-muted-foreground">暂无项目，点击「新建项目」开始设计</p>
              <Button className="mt-4" asChild>
                <Link href="/projects/new">新建项目</Link>
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border bg-card p-6 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-start gap-2">
              <Info className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <h2 className="text-lg font-semibold">方案对比概览</h2>
                <p className="text-sm text-muted-foreground">
                  全 IB 方案 vs RoCE 方案 · 5 维优劣势
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="font-normal">
                <BarChart3 className="mr-1 h-3 w-3" />
                5 维度对比
              </Badge>
              {latestWithCost && (
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/projects/${latestWithCost.id}/compare`}>
                    查看详情
                    <ExternalLink className="h-3.5 w-3.5" />
                  </Link>
                </Button>
              )}
            </div>
          </div>
          <div className="mx-auto max-w-md">
            <RadarCompare
              breakdown={costBreakdown}
              targetGpus={latestWithCost?.target_gpus ?? 512}
              embedded
            />
          </div>
        </section>
      </div>
    </div>
  );
}
