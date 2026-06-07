import { apiFetch } from "@/lib/api-client";

export type ConsultationProvider = "rule" | "openai_compatible";

export type SystemPromptPresetId =
  | "general"
  | "healthcare"
  | "training"
  | "finance"
  | "cost"
  | "custom";

export interface PromptPreset {
  id: string;
  name: string;
  description: string;
  guided_steps: string[];
  editable: boolean;
}

export interface ConsultationSettings {
  enabled: boolean;
  provider: ConsultationProvider;
  api_base_url: string;
  api_key_configured: boolean;
  model: string;
  timeout_seconds: number;
  system_prompt_preset_id: string;
  system_prompt: string;
  chat_endpoint: string;
}

export interface ConsultationSettingsUpdate {
  enabled?: boolean;
  provider?: ConsultationProvider;
  api_base_url?: string;
  api_key?: string;
  model?: string;
  timeout_seconds?: number;
  system_prompt_preset_id?: string;
  system_prompt?: string;
}

export async function getConsultationPromptPresets() {
  return apiFetch<PromptPreset[]>("/api/v1/settings/consultation/prompt-presets");
}

export async function getConsultationSettings() {
  return apiFetch<ConsultationSettings>("/api/v1/settings/consultation");
}

export async function updateConsultationSettings(payload: ConsultationSettingsUpdate) {
  return apiFetch<ConsultationSettings>("/api/v1/settings/consultation", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function testConsultationSettings(message?: string) {
  return apiFetch<{ success: boolean; message: string; provider: ConsultationProvider }>(
    "/api/v1/settings/consultation/test",
    {
      method: "POST",
      body: JSON.stringify({ message: message ?? "为医院提供10P算力" }),
    }
  );
}
