"use client";

import { Loader2, Network } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useProjectStore } from "@/lib/stores/project-store";
import type { ProjectScenario } from "@/types";

export function ParamPanel() {
  const params = useProjectStore((s) => s.params);
  const topology = useProjectStore((s) => s.topology);
  const setParams = useProjectStore((s) => s.setParams);
  const runGenerateTopology = useProjectStore((s) => s.runGenerateTopology);
  const isGenerating = useProjectStore((s) => s.isGenerating);

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-background">
      <div className="border-b px-4 py-4">
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

        <div className="space-y-1.5">
          <Label htmlFor="network_arch" className="text-xs">Network Arch</Label>
          <Select id="network_arch" className="h-9" value={params.network_arch} disabled>
            <option value="FAT_TREE">FAT_TREE</option>
          </Select>
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
          <div className="p-4">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              拓扑摘要
            </h3>
            <dl className="space-y-2 text-sm">
              {[
                ["计算节点", `${topology.compute.servers} 台`],
                ["每节点 GPU", `${params.gpus_per_node} 张`],
                ["总 GPU", `${topology.compute.gpus} 张`],
                ["Leaf 交换机", `${topology.network.leaf_switches} 台`],
                ["Spine 交换机", `${topology.network.spine_switches} 台`],
                ["400G 光模块", `${topology.network.optics_400g} 个`],
                ["存储节点", `${topology.storage.nodes} 个`],
                ["网络架构", params.network_arch],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </>
      )}
    </div>
  );
}
