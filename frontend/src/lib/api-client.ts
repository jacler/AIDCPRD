const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function parseApiError(status: number, body: string): string {
  try {
    const json = JSON.parse(body) as { detail?: string | Array<{ msg: string }> };
    if (typeof json.detail === "string") {
      if (json.detail === "Not Found") {
        return `接口不存在 (HTTP ${status})，请确认后端地址为 ${API_BASE} 且路径包含 /api/v1`;
      }
      return json.detail;
    }
    if (Array.isArray(json.detail)) {
      return json.detail.map((d) => d.msg).join("; ");
    }
  } catch {
    // not JSON
  }
  return body || `API error: ${status}`;
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(parseApiError(res.status, error));
  }

  return res.json() as Promise<T>;
}

export { API_BASE };
