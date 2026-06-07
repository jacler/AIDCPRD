import { API_BASE, apiFetch } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth-token";

export interface VisualizationResponse {
  project_id: string;
  convergence_ratio: string;
  compute_network_svg: string;
  storage_network_svg: string;
  cabinet_layout_svg: string;
  cabinet_warnings: string[];
  metadata: Record<string, unknown>;
}

export async function getProjectVisualizations(projectId: string) {
  return apiFetch<VisualizationResponse>(`/api/v1/export/projects/${projectId}/visualizations`);
}

export async function downloadTechnicalProposal(projectId: string) {
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/export/projects/${projectId}/technical-proposal`, {
      headers,
    });
  } catch {
    throw new Error("无法连接后端服务，请确认 http://localhost:8000 已启动");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `导出失败 (${res.status})`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;\s]+)/i);
  const asciiMatch = disposition.match(/filename="([^"]+)"/);
  const filename = utf8Match
    ? decodeURIComponent(utf8Match[1])
    : asciiMatch?.[1] ?? `technical_proposal_${projectId}.docx`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
