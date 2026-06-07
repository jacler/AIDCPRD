import { API_BASE, apiFetch } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth-token";

export interface ComplianceEvaluatePayload {
  domestic_mode?: boolean;
  frameworks?: string[];
  compliance?: string;
  industry?: string;
  cross_domain?: boolean;
  network_zoned?: boolean;
  audit_logging_enabled?: boolean;
}

export interface ComplianceEvaluateResponse {
  project_id: string | null;
  project_name: string;
  overall_status: string;
  domestic_adaptation: {
    enabled: boolean;
    replacements: Array<{
      original_vendor: string;
      original_model: string;
      domestic_vendor: string;
      domestic_model: string;
      public_source: string;
    }>;
    unmatched: Array<{ vendor: string; model: string; category: string }>;
    compatibility_gaps: Array<{
      framework: string;
      target_stack: string;
      status: string;
      compatibility_gap: string;
      remediation: string;
    }>;
    frameworks_requested: string[];
  };
  security_checklist: Array<{
    item_id: string;
    title: string;
    status: string;
    status_icon: string;
    remediation: string;
    regulation_ref: string;
    engineering_note: string;
  }>;
  audit_trail: Array<{
    timestamp: string;
    step: string;
    decision: string;
    evidence: Record<string, unknown>;
  }>;
  appendix_markdown: string;
}

export async function evaluateCompliance(
  projectId: string,
  payload: ComplianceEvaluatePayload
) {
  return apiFetch<ComplianceEvaluateResponse>(
    `/api/v1/compliance/projects/${projectId}/evaluate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function downloadComplianceAppendix(projectId: string) {
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/api/v1/compliance/projects/${projectId}/appendix`, {
    headers,
  });
  if (!res.ok) throw new Error("附录下载失败");
  return res.text();
}
