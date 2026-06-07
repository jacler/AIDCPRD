"use client";

import { useCallback, useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { Loader2, Pencil, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { buildFatTreeGraph } from "@/lib/topology-graph";
import { useProjectStore } from "@/lib/stores/project-store";

export function TopologyCanvas() {
  const topology = useProjectStore((s) => s.topology);
  const editMode = useProjectStore((s) => s.topologyEditMode);
  const isSavingTopology = useProjectStore((s) => s.isSavingTopology);
  const setTopologyEditMode = useProjectStore((s) => s.setTopologyEditMode);
  const saveTopologyManual = useProjectStore((s) => s.saveTopologyManual);

  const savedLayout = useMemo(() => {
    const raw = topology?.topology as Record<string, unknown> | undefined;
    return (raw?.graph_layout as { nodes: Node[]; edges: Edge[] } | undefined) ?? null;
  }, [topology]);

  const initial = useMemo(
    () => (topology ? buildFatTreeGraph(topology, savedLayout) : { nodes: [], edges: [] }),
    [topology, savedLayout]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

  useEffect(() => {
    setNodes(initial.nodes);
    setEdges(initial.edges);
  }, [initial, setNodes, setEdges]);

  const handleSave = useCallback(() => {
    void saveTopologyManual({
      nodes: nodes.map((n) => ({ id: n.id, position: n.position })),
      edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
    });
  }, [nodes, edges, saveTopologyManual]);

  return (
    <div className="flex h-full flex-col bg-slate-50/50">
      <div className="flex items-center justify-between border-b bg-background px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">网络拓扑</h2>
          <p className="text-xs text-muted-foreground">
            Fat-Tree 三层架构 · {editMode ? "编辑模式：可拖拽节点" : "只读预览"}
          </p>
        </div>
        {topology && (
          <div className="flex gap-2">
            {!editMode ? (
              <Button size="sm" variant="outline" onClick={() => setTopologyEditMode(true)}>
                <Pencil className="mr-1 h-3.5 w-3.5" />
                编辑拓扑
              </Button>
            ) : (
              <>
                <Button size="sm" variant="outline" onClick={() => setTopologyEditMode(false)}>
                  取消
                </Button>
                <Button size="sm" onClick={handleSave} disabled={isSavingTopology}>
                  {isSavingTopology ? (
                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="mr-1 h-3.5 w-3.5" />
                  )}
                  保存修改
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      <div className="relative flex-1 min-h-0">
        {topology ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            nodesDraggable={editMode}
            nodesConnectable={false}
            elementsSelectable={editMode}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} color="hsl(214 32% 91%)" />
            <Controls showInteractive={editMode} className="!shadow-md" />
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
            <p className="text-sm">用智能咨询描述需求，或配置参数后点击「生成拓扑」</p>
          </div>
        )}
      </div>

      {topology && (
        <div className="flex gap-4 border-t bg-background px-4 py-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 bg-primary" />
            100/400G Ethernet
          </span>
          {editMode && <span className="text-primary">拖拽节点后点击「保存修改」同步 BOM</span>}
        </div>
      )}
    </div>
  );
}
