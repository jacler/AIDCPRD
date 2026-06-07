"use client";

import { Loader2, Network } from "lucide-react";

import { RequirementChat } from "@/components/designer/requirement-chat";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useProjectStore } from "@/lib/stores/project-store";
import type { ProjectScenario } from "@/types";

export function ParamPanel() {
  const project = useProjectStore((s) => s.project);
  const params = useProjectStore((s) => s.params);
  const topology = useProjectStore((s) => s.topology);
  const setParams = useProjectStore((s) => s.setParams);
  const applyExtractedAndGenerateTopology = useProjectStore(
    (s) => s.applyExtractedAndGenerateTopology
  );
  const updateTopologyCounts = useProjectStore((s) => s.updateTopologyCounts);
  const saveTopologyManual = useProjectStore((s) => s.saveTopologyManual);
  const runGenerateTopology = useProjectStore((s) => s.runGenerateTopology);
  const isGenerating = useProjectStore((s) => s.isGenerating);
  const isSavingTopology = useProjectStore((s) => s.isSavingTopology);

  return (
    <div className="flex h-full flex-col min-h-0 bg-background">
      <div className="shrink-0 p-2">
        <RequirementChat
          compact
          projectId={project?.id}
          onApplyAndGenerate={applyExtractedAndGenerateTopology}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-semibold">参数配置</h2>
          <p className="text-xs text-muted-foreground mt-0.5">调整集群规模与网络参数</p>
        </div>

        <div className="space-y-4 p-4">
        <div className="space-y-1.5">
          <Label htmlFor="target_gpus" className="text-xs">
            目标 GPU 数量
          </Label>
          <div className="flex items-center gap-2">
            <Input
              id="target_gpus"
              type="number"
              min={1}
              className="h-9"
              value={params.target_gpus}
              onChange={(e) =>
                setParams({ target_gpus: Number(e.target.value) || 1 })
              }
            />
            <span className="text-xs text-muted-foreground shrink-0">张</span>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="scenario" className="text-xs">场景</Label>
          <Select
            id="scenario"
            className="h-9"
            value={params.scenario}
            onChange={(e) =>
              setParams({ scenario: e.target.value as ProjectScenario })
            }
          >
            <option value="TRAINING">训练</option>
            <option value="INFERENCE">推理</option>
            <option value="MIXED">混合</option>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="gpus_per_node" className="text-xs">每节点 GPU</Label>
          <div className="flex items-center gap-2">
            <Input
              id="gpus_per_node"
              type="number"
              min={1}
              className="h-9"
              value={params.gpus_per_node}
              onChange={(e) =>
                setParams({ gpus_per_node: Number(e.target.value) || 8 })
              }
            />
            <span className="text-xs text-muted-foreground shrink-0">张/节点</span>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="switch_ports" className="text-xs">交换机端口</Label>
          <Input
            id="switch_ports"
            type="number"
            min={2}
            step={2}
            className="h-9"
            value={params.switch_ports}
            onChange={(e) =>
              setParams({ switch_ports: Number(e.target.value) || 64 })
            }
          />
        </div>

        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input
            type="checkbox"
            checked={params.free_scheduler_with_server}
            onChange={(e) =>
              setParams({ free_scheduler_with_server: e.target.checked })
            }
            className="h-3.5 w-3.5 rounded border-input accent-primary"
          />
          买服务器送基础调度软件
        </label>

        <Button
          className="w-full"
          onClick={runGenerateTopology}
          disabled={isGenerating}
        >
          {isGenerating ? (
            <Loader2 className="animate-spin" />
          ) : (
            <Network />
          )}
          生成拓扑
        </Button>
      </div>

      {topology && (
        <>
          <Separator />
          <div className="p-4 space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              拓扑摘要（可手动调整）
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { key: "servers", label: "计算节点", value: topology.compute.servers },
                { key: "gpus", label: "总 GPU", value: topology.compute.gpus },
                { key: "leaf", label: "Leaf", value: topology.network.leaf_switches },
                { key: "spine", label: "Spine", value: topology.network.spine_switches },
                { key: "storage", label: "存储节点", value: topology.storage.nodes },
              ].map((item) => (
                <div key={item.key} className="space-y-1">
                  <Label className="text-[10px] text-muted-foreground">{item.label}</Label>
                  <Input
                    type="number"
                    min={1}
                    className="h-8 text-xs"
                    value={item.value}
                    onChange={(e) => {
                      const v = Number(e.target.value) || 1;
                      if (item.key === "servers") updateTopologyCounts({ servers: v });
                      if (item.key === "gpus") updateTopologyCounts({ gpus: v });
                      if (item.key === "leaf") updateTopologyCounts({ leaf_switches: v });
                      if (item.key === "spine") updateTopologyCounts({ spine_switches: v });
                      if (item.key === "storage") updateTopologyCounts({ storage_nodes: v });
                    }}
                  />
                </div>
              ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              disabled={isSavingTopology}
              onClick={() => void saveTopologyManual()}
            >
              {isSavingTopology ? "保存中…" : "应用数量修改并更新 BOM"}
            </Button>
          </div>
        </>
      )}
      </div>
    </div>
  );
}
