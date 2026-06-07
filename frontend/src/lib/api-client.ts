import { clearAccessToken, getAccessToken } from "@/lib/auth-token";

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

type ApiFetchOptions = RequestInit & { skipAuth?: boolean };

function parseApiError(status: number, body: string): string {
  try {
    const json = JSON.parse(body) as { detail?: string | Array<{ msg: string }> };
    if (typeof json.detail === "string") {
      if (json.detail === "Not Found") {
        return `接口不存在 (HTTP ${status})`;
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(path: string, options?: ApiFetchOptions): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };

  if (!options?.skipAuth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !options?.skipAuth) {
    clearAccessToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new AuthError("登录已过期，请重新登录");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  if (!res.ok) {
    const error = await res.text();
    throw new Error(parseApiError(res.status, error));
  }

  return res.json() as Promise<T>;
}

export { API_BASE };
