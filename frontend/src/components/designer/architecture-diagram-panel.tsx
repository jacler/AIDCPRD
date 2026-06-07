"use client";

import { useCallback, useState } from "react";
import { Copy, Layers, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { generateProjectDiagram, type DiagramGenerateResponse } from "@/lib/api/diagrams";

interface ArchitectureDiagramPanelProps {
  projectId: string;
  projectName?: string;
  targetGpus?: number;
}

export function ArchitectureDiagramPanel({
  projectId,
  projectName,
  targetGpus,
}: ArchitectureDiagramPanelProps) {
  const [loading, setLoading] = useState(false);
  const [exportMode, setExportMode] = useState<"web_interactive" | "ppt_ready" | "doc_embed">(
    "web_interactive"
  );
  const [result, setResult] = useState<DiagramGenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateProjectDiagram(projectId, {
        requirement: projectName ?? "智算集群",
        target_gpus: targetGpus,
        export_mode: exportMode,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }, [projectId, projectName, targetGpus, exportMode]);

  const copyCode = () => {
    if (result?.mermaid_code) void navigator.clipboard.writeText(result.mermaid_code);
  };

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Layers className="h-4 w-4 text-primary" />
              工程级架构图
            </CardTitle>
            <CardDescription>
              AIDC V4.0 · Mermaid 语法合规 · 交付级架构图
            </CardDescription>
          </div>
          <div className="flex gap-1">
            {(["web_interactive", "ppt_ready", "doc_embed"] as const).map((m) => (
              <Button
                key={m}
                size="sm"
                variant={exportMode === m ? "default" : "outline"}
                className="h-7 text-xs"
                onClick={() => setExportMode(m)}
              >
                {m === "ppt_ready" ? "PPT" : m === "doc_embed" ? "Word" : "Web"}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button size="sm" onClick={() => void handleGenerate()} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="mr-1 h-3.5 w-3.5" />
          )}
          生成架构图
        </Button>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && (
          <>
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <p className="font-medium">{result.pattern_name}</p>
              <p className="text-muted-foreground">
                收敛比 {result.convergence_ratio} · {result.figure_caption}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                {result.design_points.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>

            {result.compliance_checklist?.length > 0 && (
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-2 text-xs">
                {result.compliance_checklist.map((c) => (
                  <p key={c}>{c}</p>
                ))}
              </div>
            )}

            {result.model_warnings?.length > 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs">
                {result.model_warnings.map((w) => (
                  <p key={w}>⚠️ {w}</p>
                ))}
              </div>
            )}

            {result.param_table && (
              <pre className="max-h-40 overflow-auto rounded-md border bg-muted/30 p-2 text-[10px]">
                {result.param_table}
              </pre>
            )}

            <div className="relative">
              <Button
                size="sm"
                variant="outline"
                className="absolute right-2 top-2 z-10 h-7"
                onClick={copyCode}
              >
                <Copy className="mr-1 h-3 w-3" />
                复制 Mermaid
              </Button>
              <pre className="max-h-64 overflow-auto rounded-md border bg-slate-950 p-3 text-[10px] leading-relaxed text-slate-100">
                {result.mermaid_code}
              </pre>
            </div>

            <div className="text-xs text-muted-foreground">
              <p className="font-medium text-foreground">推荐渲染工具</p>
              {result.render_tools.map((t) => (
                <p key={t.name}>
                  {t.url ? (
                    <a href={t.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                      {t.name}
                    </a>
                  ) : (
                    t.name
                  )}
                  — {t.export}
                </p>
              ))}
              <p className="mt-1 italic">{result.data_disclaimer}</p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
