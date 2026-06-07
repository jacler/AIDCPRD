import { MarkerType, type Edge, type Node } from "reactflow";

import type { GenerateTopologyResponse } from "@/types";

const SPINE_STYLE = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid hsl(221 83% 53%)",
  background: "hsl(221 83% 97%)",
  fontSize: 11,
  fontWeight: 600,
  minWidth: 36,
  textAlign: "center" as const,
};

const LEAF_STYLE = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid hsl(214 32% 80%)",
  background: "hsl(210 40% 98%)",
  fontSize: 11,
  fontWeight: 500,
  minWidth: 36,
  textAlign: "center" as const,
};

const COMPUTE_STYLE = {
  padding: "4px 8px",
  borderRadius: 4,
  border: "1px solid hsl(214 32% 85%)",
  background: "hsl(0 0% 100%)",
  fontSize: 10,
  minWidth: 32,
  textAlign: "center" as const,
};

function rowPositions(count: number, spacing: number, startX: number): number[] {
  const width = (count - 1) * spacing;
  const offset = startX - width / 2;
  return Array.from({ length: count }, (_, i) => offset + i * spacing);
}

type GraphLayout = {
  nodes?: { id: string; position: { x: number; y: number } }[];
  edges?: { id: string; source: string; target: string }[];
};

export function buildFatTreeGraph(
  topology: GenerateTopologyResponse,
  savedLayout?: GraphLayout | null
): {
  nodes: Node[];
  edges: Edge[];
} {
  const { compute, network } = topology;
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const spineCount = network.spine_switches;
  const leafCount = network.leaf_switches;
  const serverCount = compute.servers;

  const spineXs = rowPositions(spineCount, 72, 400);
  spineXs.forEach((x, i) => {
    const id = `spine-${i}`;
    nodes.push({
      id,
      position: { x, y: 0 },
      data: { label: `S${i + 1}` },
      style: SPINE_STYLE,
    });
  });

  const leafXs = rowPositions(leafCount, 48, 400);
  leafXs.forEach((x, i) => {
    const id = `leaf-${i}`;
    nodes.push({
      id,
      position: { x, y: 100 },
      data: { label: `L${i + 1}` },
      style: LEAF_STYLE,
    });

    const spineIdx = i % spineCount;
    edges.push({
      id: `e-spine-leaf-${i}`,
      source: `spine-${spineIdx}`,
      target: id,
      style: { stroke: "hsl(221 83% 53%)", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12 },
    });
  });

  const visibleServers = Math.min(serverCount, 16);
  const serverXs = rowPositions(visibleServers, 44, 400);
  serverXs.forEach((x, i) => {
    const id = `compute-${i}`;
    nodes.push({
      id,
      position: { x, y: 220 },
      data: { label: `C${i + 1}` },
      style: COMPUTE_STYLE,
    });

    const leafIdx = i % leafCount;
    edges.push({
      id: `e-leaf-compute-${i}`,
      source: `leaf-${leafIdx}`,
      target: id,
      style: { stroke: "hsl(215 16% 65%)", strokeWidth: 1 },
    });
  });

  if (serverCount > visibleServers) {
    nodes.push({
      id: "compute-more",
      position: { x: 400, y: 280 },
      data: { label: `+${serverCount - visibleServers} 台` },
      style: { ...COMPUTE_STYLE, borderStyle: "dashed", color: "hsl(215 16% 46%)" },
    });
  }

  nodes.unshift({
    id: "layer-spine",
    position: { x: 20, y: 4 },
    data: { label: `Spine 层 (${spineCount} 台)` },
    style: {
      border: "none",
      background: "transparent",
      fontSize: 12,
      fontWeight: 600,
      color: "hsl(221 83% 53%)",
      padding: 0,
    },
    draggable: false,
  });

  nodes.push({
    id: "layer-leaf",
    position: { x: 20, y: 104 },
    data: { label: `Leaf 层 (${leafCount} 台)` },
    style: {
      border: "none",
      background: "transparent",
      fontSize: 12,
      fontWeight: 600,
      padding: 0,
    },
    draggable: false,
  });

  nodes.push({
    id: "layer-compute",
    position: { x: 20, y: 224 },
    data: { label: `计算节点层 (${serverCount} 台 · ${compute.gpus} GPU)` },
    style: {
      border: "none",
      background: "transparent",
      fontSize: 12,
      fontWeight: 600,
      padding: 0,
    },
    draggable: false,
  });

  if (savedLayout?.nodes?.length) {
    const posMap = new Map(savedLayout.nodes.map((n) => [n.id, n.position]));
    for (const node of nodes) {
      const saved = posMap.get(node.id);
      if (saved) node.position = saved;
    }
  }

  if (savedLayout?.edges?.length) {
    return {
      nodes,
      edges: savedLayout.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        style: { stroke: "hsl(221 83% 53%)", strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12 },
      })),
    };
  }

  return { nodes, edges };
}
