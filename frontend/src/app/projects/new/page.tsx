"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";

import { RequirementChat } from "@/components/designer/requirement-chat";
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
import {
  applyConsultationPlan,
  type ExtractedRequirements,
} from "@/lib/api/consultation";
import { createProject } from "@/lib/api/projects";
import type { ProjectScenario } from "@/types";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("512卡训练集群");
  const [targetGpus, setTargetGpus] = useState(512);
  const [scenario, setScenario] = useState<ProjectScenario>("TRAINING");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applyExtracted(extracted: ExtractedRequirements) {
    if (extracted.project_name) setName(extracted.project_name);
    if (extracted.target_gpus) setTargetGpus(extracted.target_gpus);
    if (extracted.scenario) setScenario(extracted.scenario);
    if (extracted.description) setDescription(extracted.description);
    if (extracted.scheme_summary) {
      setDescription((prev) =>
        prev ? `${prev}\n\n方案：${extracted.scheme_summary}` : extracted.scheme_summary ?? ""
      );
    }
  }

  async function applyPlanAndCreate(extracted: ExtractedRequirements) {
    applyExtracted(extracted);
    const result = await applyConsultationPlan({
      extracted,
      requirement_text: extracted.scheme_summary ?? extracted.description ?? undefined,
    });
    router.push(`/projects/${result.project_id}/designer`);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const project = await createProject({
        name,
        target_gpus: targetGpus,
        scenario,
        description: description || undefined,
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

      <div className="mx-auto max-w-2xl px-6 py-12 space-y-6">
        <RequirementChat onApplyPlan={applyPlanAndCreate} onApply={applyExtracted} />

        <Card className="shadow-md">
          <CardHeader>
            <CardTitle>需求定义向导</CardTitle>
            <CardDescription>
              可通过上方对话描述需求，或手动填写参数后创建项目
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

              {description && (
                <div className="rounded-md border bg-muted/40 p-3 text-xs text-muted-foreground whitespace-pre-wrap">
                  {description}
                </div>
              )}

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
