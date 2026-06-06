"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Loader2, Server } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listProjects } from "@/lib/api/projects";
import { SCENARIO_LABELS, STATUS_LABELS } from "@/types";

export function ProjectList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: () => listProjects(),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-destructive">
        无法加载项目列表，请确认后端服务已启动 (localhost:8000)
      </p>
    );
  }

  if (!data?.items.length) {
    return (
      <p className="text-sm text-muted-foreground">
        暂无项目。点击「新建项目」开始设计 Fat-Tree 拓扑与 BOM 成本拆解。
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.items.map((project) => (
        <Card key={project.id} className="hover:shadow-md transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-base leading-snug">
                {project.name}
              </CardTitle>
              <Badge variant="secondary" className="shrink-0">
                {SCENARIO_LABELS[project.scenario]}
              </Badge>
            </div>
            <CardDescription>
              {project.target_gpus} GPU · {STATUS_LABELS[project.status]}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm" className="w-full">
              <Link href={`/projects/${project.id}/designer`}>
                进入设计器
                <ArrowRight />
              </Link>
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function DashboardHeader() {
  return (
    <header className="border-b bg-background">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <Server className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">AIDC-CostPro</span>
        </div>
        <Button asChild>
          <Link href="/projects/new">新建项目</Link>
        </Button>
      </div>
    </header>
  );
}
