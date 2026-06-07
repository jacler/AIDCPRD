import { API_BASE, apiFetch } from "@/lib/api-client";
import { clearAccessToken, getAccessToken } from "@/lib/auth-token";
import type { ProjectScenario } from "@/types";

export interface ExtractedRequirements {
  target_gpus: number | null;
  scenario: ProjectScenario | null;
  gpus_per_node: number | null;
  switch_ports: number | null;
  network_arch: string | null;
  free_scheduler_with_server: boolean | null;
  industry: string | null;
  compute_pflops: number | null;
  project_name: string | null;
  description: string | null;
  compliance: string | null;
  scheme_summary: string | null;
}

export interface ConsultationMessage {
  role: string;
  content: string;
}

export interface ConsultationResponse {
  session_id: string;
  reply: string;
  questions: string[];
  ready_to_generate: boolean;
  extracted: ExtractedRequirements | null;
  messages: ConsultationMessage[];
  engine: "rule" | "openai_compatible";
}

export interface StreamConsultationOptions {
  message: string;
  sessionId?: string;
  projectId?: string;
  onToken: (delta: string) => void;
  signal?: AbortSignal;
}

function sessionStorageKey(projectId?: string) {
  return `consultation:session:${projectId ?? "draft"}`;
}

function messagesStorageKey(projectId?: string) {
  return `consultation:messages:${projectId ?? "draft"}`;
}

export function loadStoredSessionId(projectId?: string): string | undefined {
  if (typeof window === "undefined") return undefined;
  return sessionStorage.getItem(sessionStorageKey(projectId)) ?? undefined;
}

export function loadStoredMessages(projectId?: string): ConsultationMessage[] {
  if (typeof window === "undefined") return [];
  const raw = sessionStorage.getItem(messagesStorageKey(projectId));
  if (!raw) return [];
  try {
    return JSON.parse(raw) as ConsultationMessage[];
  } catch {
    return [];
  }
}

export function storeSessionId(projectId: string | undefined, sessionId: string) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(sessionStorageKey(projectId), sessionId);
}

export function storeMessages(projectId: string | undefined, messages: ConsultationMessage[]) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(messagesStorageKey(projectId), JSON.stringify(messages));
}

export function clearStoredSessionId(projectId?: string) {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(sessionStorageKey(projectId));
  sessionStorage.removeItem(messagesStorageKey(projectId));
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value
  );
}

/** Only real project UUIDs are sent to the API; draft/new-project uses null. */
export function isValidProjectId(projectId?: string): boolean {
  return !!projectId && isUuid(projectId);
}

function toApiProjectId(projectId?: string): string | null {
  if (!isValidProjectId(projectId)) return null;
  return projectId!;
}

function parseSseEvent(raw: string): { eventType: string; dataLine: string } | null {
  if (!raw.trim()) return null;

  let eventType = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  return { eventType, dataLine: dataLines.join("\n") };
}

function handleSseEvent(
  event: { eventType: string; dataLine: string },
  onToken: (delta: string) => void
): ConsultationResponse | null {
  const payload = JSON.parse(event.dataLine) as Record<string, unknown>;
  if (event.eventType === "token" && typeof payload.delta === "string") {
    onToken(payload.delta);
    return null;
  }
  if (event.eventType === "done" && payload.data) {
    return payload.data as ConsultationResponse;
  }
  if (event.eventType === "error") {
    throw new Error(String(payload.message ?? "咨询失败"));
  }
  return null;
}

export async function streamConsultationMessage(
  options: StreamConsultationOptions
): Promise<ConsultationResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/v1/consultation/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message: options.message,
      session_id: options.sessionId ?? null,
      project_id: toApiProjectId(options.projectId),
    }),
    signal: options.signal,
  });

  if (res.status === 401) {
    clearAccessToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new Error("登录已过期，请重新登录");
  }

  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `API error: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("流式响应不可用");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let result: ConsultationResponse | null = null;

  const processBuffer = (flushAll = false) => {
    const separator = "\n\n";
    let idx = buffer.indexOf(separator);
    while (idx !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + separator.length);
      const event = parseSseEvent(raw);
      if (event) {
        const done = handleSseEvent(event, options.onToken);
        if (done) result = done;
      }
      idx = buffer.indexOf(separator);
    }
    if (flushAll && buffer.trim()) {
      const event = parseSseEvent(buffer);
      buffer = "";
      if (event) {
        const done = handleSseEvent(event, options.onToken);
        if (done) result = done;
      }
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: !done });
      processBuffer(false);
    }
    if (done) {
      buffer += decoder.decode();
      processBuffer(true);
      break;
    }
  }

  if (!result) {
    throw new Error("未收到完整响应");
  }
  return result;
}

export interface ApplyPlanPayload {
  extracted: ExtractedRequirements;
  project_id?: string;
  requirement_text?: string;
  import_skus?: boolean;
}

export interface ApplyPlanResponse {
  project_id: string;
  project_name: string;
  ready_to_generate: boolean;
  topology: Record<string, unknown> | null;
  topology_result: {
    compute: { servers: number; gpus: number };
    network: {
      leaf_switches: number;
      spine_switches: number;
      rdma_nics: number;
      dac_cables: number;
      optics_400g: number;
    };
    storage: { nodes: number };
    bom: Array<{
      sku_id: string | null;
      category: string;
      model: string;
      quantity: number;
      unit_price: number | string;
      total_price: number | string;
      cost_dimension: string;
    }>;
    topology: Record<string, unknown>;
  } | null;
  bom_count: number;
  skus_imported: number;
  sku_search_note: string;
  message: string;
}

export async function applyConsultationPlan(payload: ApplyPlanPayload) {
  return apiFetch<ApplyPlanResponse>("/api/v1/consultation/apply-plan", {
    method: "POST",
    body: JSON.stringify({
      extracted: payload.extracted,
      project_id: payload.project_id ?? null,
      requirement_text: payload.requirement_text ?? null,
      import_skus: payload.import_skus ?? true,
    }),
  });
}
