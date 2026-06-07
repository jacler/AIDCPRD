import { apiFetch } from "@/lib/api-client";
import { clearAccessToken, setAccessToken, setStoredUser } from "@/lib/auth-token";
import type { PaginatedResponse, UserAccount } from "@/types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  display_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserAccount;
}

export async function login(payload: LoginPayload) {
  const data = await apiFetch<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
  setAccessToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function register(payload: RegisterPayload) {
  return apiFetch<UserAccount>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
}

export async function getMe() {
  return apiFetch<UserAccount>("/api/v1/auth/me");
}

export async function changePassword(currentPassword: string, newPassword: string) {
  return apiFetch<void>("/api/v1/auth/me/password", {
    method: "PUT",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export async function listUsers(page = 1, pageSize = 20) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return apiFetch<PaginatedResponse<UserAccount>>(`/api/v1/auth/users?${params}`);
}

export async function createUser(payload: RegisterPayload & { role?: "ADMIN" | "USER" }) {
  return apiFetch<UserAccount>("/api/v1/auth/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUser(
  userId: string,
  payload: Partial<{ display_name: string; role: "ADMIN" | "USER"; is_active: boolean }>
) {
  return apiFetch<UserAccount>(`/api/v1/auth/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function logout() {
  clearAccessToken();
}
