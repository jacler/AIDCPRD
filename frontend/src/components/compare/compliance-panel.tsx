"use client";

import { useMutation } from "@tanstack/react-query";
import { Download, Loader2, Shield } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  downloadComplianceAppendix,
  evaluateCompliance,
  type ComplianceEvaluateResponse,
} from "@/lib/api/compliance";

interface CompliancePanelProps {
  projectId: string;
}

export function CompliancePanel({ projectId }: CompliancePanelProps) {
  const [domesticMode, setDomesticMode] = useState(false);
  const [frameworks, setFrameworks] = useState("pytorch");
  const [result, setResult] = useState<ComplianceEvaluateResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      evaluateCompliance(projectId, {
        domestic_mode: domesticMode,
        frameworks: frameworks.split(",").map((f) => f.trim()).filter(Boolean),
        cross_domain: false,
        network_zoned: false,
        audit_logging_enabled: false,
      }),
    onSuccess: (data) => setResult(data),
  });

  async function handleDownloadAppendix() {
    const md = result?.appendix_markdown ?? (await downloadComplianceAppendix(projectId));
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `compliance-appendix-${projectId.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">动态合规适配</CardTitle>
        </div>
        <CardDescription>
          信创替换 · 框架兼容性 · 等保自查（GB/T 22239-2019）
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={domesticMode}
            onChange={(e) => setDomesticMode(e.target.checked)}
            className="h-4 w-4 accent-primary"
          />
          启用信创模式（国产化替代）
        </label>
        <div className="space-y-1">
          <Label className="text-xs">AI 框架（逗号分隔）</Label>
          <input
            className="w-full rounded-md border bg-background px-2 py-1.5 text-sm"
            value={frameworks}
            onChange={(e) => setFrameworks(e.target.value)}
            placeholder="pytorch, deepspeed"
          />
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            执行合规评估
          </Button>
          {result && (
            <Button size="sm" variant="outline" onClick={() => void handleDownloadAppendix()}>
              <Download className="mr-1 h-4 w-4" />
              导出合规附录
            </Button>
          )}
        </div>

        {mutation.error && (
          <p className="text-sm text-destructive">
            {mutation.error instanceof Error ? mutation.error.message : "评估失败"}
          </p>
        )}

        {result && (
          <div className="space-y-4 border-t pt-4">
            <p className="text-sm">
              综合状态：
              <span className="font-semibold">{result.overall_status.toUpperCase()}</span>
            </p>

            {result.domestic_adaptation.enabled &&
              result.domestic_adaptation.compatibility_gaps.length > 0 && (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs">
                  <p className="mb-2 font-medium text-amber-900">⚠️ 框架兼容性缺口</p>
                  {result.domestic_adaptation.compatibility_gaps.map((g, i) => (
                    <div key={i} className="mb-2 text-amber-800">
                      <p>
                        <strong>{g.framework}</strong> ({g.status})：{g.compatibility_gap}
                      </p>
                      <p className="text-muted-foreground">补救：{g.remediation}</p>
                    </div>
                  ))}
                </div>
              )}

            {result.domestic_adaptation.enabled &&
              result.domestic_adaptation.replacements.length > 0 && (
                <div className="text-xs text-muted-foreground">
                  <p className="mb-1 font-medium text-foreground">信创替换映射</p>
                  <ul className="list-disc pl-4 space-y-1">
                    {result.domestic_adaptation.replacements.map((r, i) => (
                      <li key={i}>
                        {r.original_vendor} {r.original_model} → {r.domestic_vendor}{" "}
                        {r.domestic_model}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            <div className="text-xs">
              <p className="mb-2 font-medium">等保自查项</p>
              <ul className="space-y-2">
                {result.security_checklist.map((item) => (
                  <li key={item.item_id} className="rounded border p-2">
                    <p>
                      {item.status_icon} {item.title}
                    </p>
                    <p className="text-muted-foreground">{item.regulation_ref}</p>
                    <p className="mt-1">{item.remediation}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
