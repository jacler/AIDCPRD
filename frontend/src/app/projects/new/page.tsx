"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";

import { MainNav } from "@/components/layout/main-nav";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { createProject } from "@/lib/api/projects";
import type { ProjectScenario } from "@/types";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("512卡训练集群");
  const [targetGpus, setTargetGpus] = useState(512);
  const [scenario, setScenario] = useState<ProjectScenario>("TRAINING");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const project = await createProject({
        name,
        target_gpus: targetGpus,
        scenario,
      });
      router.push(`/projects/${project.id}/designer`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav />

      <div className="mx-auto max-w-lg px-6 py-12">
        <Card className="shadow-md">
          <CardHeader>
            <CardTitle>需求定义向导</CardTitle>
            <CardDescription>
              输入 GPU 数量与应用场景，创建后进入设计器
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">项目名称</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="gpus">目标 GPU 数量</Label>
                <Input
                  id="gpus"
                  type="number"
                  min={1}
                  value={targetGpus}
                  onChange={(e) => setTargetGpus(Number(e.target.value) || 1)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="scenario">应用场景</Label>
                <Select
                  id="scenario"
                  value={scenario}
                  onChange={(e) =>
                    setScenario(e.target.value as ProjectScenario)
                  }
                >
                  <option value="TRAINING">训练 (TRAINING)</option>
                  <option value="INFERENCE">推理 (INFERENCE)</option>
                  <option value="MIXED">混合 (MIXED)</option>
                </Select>
              </div>

              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}

              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={loading} className="flex-1">
                  {loading && <Loader2 className="animate-spin" />}
                  创建并进入设计器
                </Button>
                <Button type="button" variant="outline" asChild>
                  <Link href="/">取消</Link>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
