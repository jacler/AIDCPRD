"use client";

import { MainNav } from "@/components/layout/main-nav";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav showNewProject />

      <div className="mx-auto max-w-lg px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">设置</h1>

        <div className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <div className="space-y-2">
            <Label>后端 API 地址</Label>
            <Input
              readOnly
              value={process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
            />
            <p className="text-xs text-muted-foreground">
              修改请编辑 frontend/.env.local 中的 NEXT_PUBLIC_API_URL
            </p>
          </div>
          <div className="space-y-2">
            <Label>默认网络架构</Label>
            <Input readOnly value="Fat-Tree (无收敛)" />
          </div>
          <div className="space-y-2">
            <Label>隐性基建成本比例</Label>
            <Input readOnly value="5% (硬件小计)" />
          </div>
        </div>
      </div>
    </div>
  );
}
