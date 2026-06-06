"use client";

import { useEffect } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import { DesignerHeader } from "@/components/designer/designer-header";
import { DesignerRightPanel } from "@/components/designer/designer-right-panel";
import { ParamPanel } from "@/components/designer/param-panel";
import { TopologyCanvas } from "@/components/designer/topology-canvas";
import { useProjectStore } from "@/lib/stores/project-store";

interface DesignerPageProps {
  projectId: string;
}

export function DesignerWorkspace({ projectId }: DesignerPageProps) {
  const project = useProjectStore((s) => s.project);
  const error = useProjectStore((s) => s.error);
  const loadProject = useProjectStore((s) => s.loadProject);
  const reset = useProjectStore((s) => s.reset);

  useEffect(() => {
    void loadProject(projectId);
    return () => reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  if (!project) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <DesignerHeader />

      {error && (
        <div className="mx-4 mt-2 flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span className="truncate">{error}</span>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        <aside className="w-[280px] shrink-0 overflow-hidden border-r">
          <ParamPanel />
        </aside>
        <main className="flex-1 min-w-0 overflow-hidden">
          <TopologyCanvas />
        </main>
        <DesignerRightPanel projectId={projectId} />
      </div>
    </div>
  );
}
