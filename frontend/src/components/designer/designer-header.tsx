"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronRight, FileText, Hexagon, Save, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadTechnicalProposal } from "@/lib/api/export";
import { exportBomToCsv } from "@/lib/export-bom";
import { useProjectStore } from "@/lib/stores/project-store";

export function DesignerHeader() {
  const project = useProjectStore((s) => s.project);
  const bom = useProjectStore((s) => s.bom);
  const topology = useProjectStore((s) => s.topology);
  const saveProject = useProjectStore((s) => s.saveProject);
  const isSaving = useProjectStore((s) => s.isSaving);
  const [exportingDoc, setExportingDoc] = useState(false);

  if (!project) return null;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-1.5 text-sm font-semibold">
          <Hexagon className="h-5 w-5 fill-primary text-primary" />
          <span className="hidden sm:inline">AIDC-CostPro</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm text-muted-foreground">
          <Link href="/" className="hover:text-primary">
            项目
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="max-w-[180px] truncate text-foreground">{project.name}</span>
          <ChevronRight className="h-4 w-4" />
          <span className="font-medium text-primary">设计器</span>
        </nav>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={isSaving}
          onClick={() => void saveProject()}
        >
          <Save className="h-4 w-4" />
          {isSaving ? "保存中…" : "保存"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!topology || exportingDoc}
          onClick={() => {
            setExportingDoc(true);
            void downloadTechnicalProposal(project.id).finally(() => setExportingDoc(false));
          }}
        >
          <FileText className="h-4 w-4" />
          {exportingDoc ? "生成中…" : "技术方案书"}
        </Button>
        <Button
          size="sm"
          disabled={bom.length === 0}
          onClick={() => exportBomToCsv(bom, project.name)}
        >
          <Upload className="h-4 w-4" />
          导出 BOM
        </Button>
      </div>
    </header>
  );
}
