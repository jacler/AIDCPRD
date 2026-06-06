"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";

import { buildFatTreeGraph } from "@/lib/topology-graph";
import { useProjectStore } from "@/lib/stores/project-store";

export function TopologyCanvas() {
  const topology = useProjectStore((s) => s.topology);

  const { nodes, edges } = useMemo(
    () => (topology ? buildFatTreeGraph(topology) : { nodes: [], edges: [] }),
    [topology]
  );

  return (
    <div className="flex h-full flex-col bg-slate-50/50">
      <div className="flex items-center justify-between border-b bg-background px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">网络拓扑</h2>
          <p className="text-xs text-muted-foreground">Fat-Tree 三层架构 · 100/400G RDMA</p>
        </div>
      </div>

      <div className="relative flex-1 min-h-0">
        {topology ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} color="hsl(214 32% 91%)" />
            <Controls showInteractive={false} className="!shadow-md" />
            <MiniMap
              nodeColor={() => "hsl(221 83% 53%)"}
              maskColor="hsl(0 0% 100% / 0.7)"
              className="!border !shadow-md"
            />
          </ReactFlow>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
            <div className="rounded-full bg-primary/10 p-4">
              <svg className="h-8 w-8 text-primary/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <p className="text-sm">配置左侧参数后，点击「生成拓扑」</p>
          </div>
        )}
      </div>

      {topology && (
        <div className="flex gap-4 border-t bg-background px-4 py-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 bg-primary" />
            100/400G Ethernet
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 border-t border-dashed border-muted-foreground" />
            GPU Interconnect
          </span>
        </div>
      )}
    </div>
  );
}
