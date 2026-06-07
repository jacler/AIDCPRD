"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { MainNav } from "@/components/layout/main-nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { changePassword } from "@/lib/api/auth";
import {
  getConsultationPromptPresets,
  getConsultationSettings,
  testConsultationSettings,
  updateConsultationSettings,
  type ConsultationProvider,
  type ConsultationSettings,
  type PromptPreset,
  type SystemPromptPresetId,
} from "@/lib/api/settings";
import { API_BASE } from "@/lib/api-client";

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [consultation, setConsultation] = useState<ConsultationSettings | null>(null);
  const [consultForm, setConsultForm] = useState({
    enabled: true,
    provider: "rule" as ConsultationProvider,
    api_base_url: "https://api.openai.com/v1",
    api_key: "",
    model: "gpt-4o-mini",
    timeout_seconds: 60,
    system_prompt_preset_id: "general" as SystemPromptPresetId,
    system_prompt: "",
  });
  const [promptPresets, setPromptPresets] = useState<PromptPreset[]>([]);
  const [consultMsg, setConsultMsg] = useState("");
  const [consultErr, setConsultErr] = useState("");
  const [consultSaving, setConsultSaving] = useState(false);
  const [consultTesting, setConsultTesting] = useState(false);

  useEffect(() => {
    void Promise.all([getConsultationSettings(), getConsultationPromptPresets()])
      .then(([data, presets]) => {
        setPromptPresets(presets);
        setConsultation(data);
        setConsultForm((f) => ({
          ...f,
          enabled: data.enabled,
          provider: data.provider,
          api_base_url: data.api_base_url,
          model: data.model,
          timeout_seconds: data.timeout_seconds,
          system_prompt_preset_id: (data.system_prompt_preset_id ||
            "custom") as SystemPromptPresetId,
          system_prompt: data.system_prompt,
        }));
      })
      .catch((err) => setConsultErr(err instanceof Error ? err.message : "加载咨询配置失败"));
  }, []);

  const selectedPreset = promptPresets.find(
    (p) => p.id === consultForm.system_prompt_preset_id
  );
  const isCustomPrompt = consultForm.system_prompt_preset_id === "custom";

  async function handlePasswordChange(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    setError("");
    setSaving(true);
    try {
      await changePassword(currentPassword, newPassword);
      setMessage("密码已更新");
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "修改失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleConsultationSave(e: FormEvent) {
    e.preventDefault();
    if (!isAdmin) return;
    setConsultMsg("");
    setConsultErr("");
    setConsultSaving(true);
    try {
      const payload: Record<string, unknown> = {
        enabled: consultForm.enabled,
        provider: consultForm.provider,
        api_base_url: consultForm.api_base_url,
        model: consultForm.model,
        timeout_seconds: consultForm.timeout_seconds,
        system_prompt_preset_id: consultForm.system_prompt_preset_id,
      };
      if (consultForm.system_prompt_preset_id === "custom") {
        payload.system_prompt = consultForm.system_prompt;
      }
      if (consultForm.api_key.trim()) {
        payload.api_key = consultForm.api_key.trim();
      }
      const updated = await updateConsultationSettings(payload);
      setConsultation(updated);
      setConsultForm((f) => ({ ...f, api_key: "" }));
      setConsultMsg("智能咨询配置已保存");
    } catch (err) {
      setConsultErr(err instanceof Error ? err.message : "保存失败");
    } finally {
      setConsultSaving(false);
    }
  }

  async function handleConsultationTest() {
    if (!isAdmin) return;
    setConsultMsg("");
    setConsultErr("");
    setConsultTesting(true);
    try {
      const result = await testConsultationSettings();
      setConsultMsg(result.message);
    } catch (err) {
      setConsultErr(err instanceof Error ? err.message : "测试失败");
    } finally {
      setConsultTesting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav showNewProject />

      <div className="mx-auto max-w-2xl px-6 py-8 space-y-6">
        <h1 className="text-2xl font-bold">设置</h1>

        <div className="space-y-4 rounded-xl border bg-card p-6 shadow-sm">
          <div className="space-y-1">
            <Label>当前账号</Label>
            <p className="text-sm font-medium">{user?.display_name}</p>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>
          <div className="space-y-2">
            <Label>后端 API 地址</Label>
            <Input readOnly value={process.env.NEXT_PUBLIC_API_URL ?? API_BASE} />
          </div>
        </div>

        <form
          onSubmit={handleConsultationSave}
          className="space-y-4 rounded-xl border bg-card p-6 shadow-sm"
        >
          <div>
            <h2 className="font-semibold">智能需求咨询</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              默认使用规则引擎（模板回复）。选择「OpenAI 兼容 API」并填写 API Key、模型名称后，
              咨询将调用大模型生成个性化方案，并自动提取 GPU 规模、网络参数等配置。
            </p>
          </div>

          {consultation && (
            <div className="rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
              咨询接口：<code>{API_BASE}{consultation.chat_endpoint}</code>
              {consultation.api_key_configured && " · API Key 已配置"}
            </div>
          )}

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={consultForm.enabled}
              disabled={!isAdmin}
              onChange={(e) => setConsultForm((f) => ({ ...f, enabled: e.target.checked }))}
              className="h-4 w-4 accent-primary"
            />
            启用智能需求咨询
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>咨询引擎</Label>
              <Select
                value={consultForm.provider}
                disabled={!isAdmin}
                onChange={(e) =>
                  setConsultForm((f) => ({
                    ...f,
                    provider: e.target.value as ConsultationProvider,
                  }))
                }
              >
                <option value="rule">规则引擎（内置，无需 API）</option>
                <option value="openai_compatible">OpenAI 兼容 API</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>超时（秒）</Label>
              <Input
                type="number"
                min={5}
                max={300}
                disabled={!isAdmin}
                value={consultForm.timeout_seconds}
                onChange={(e) =>
                  setConsultForm((f) => ({
                    ...f,
                    timeout_seconds: Number(e.target.value) || 60,
                  }))
                }
              />
            </div>
          </div>

          {consultForm.provider === "openai_compatible" && (
            <>
              <div className="space-y-2">
                <Label>快速选择服务商</Label>
                <div className="flex flex-wrap gap-2">
                  {[
                    {
                      label: "OpenAI",
                      api_base_url: "https://api.openai.com/v1",
                      model: "gpt-4o-mini",
                    },
                    {
                      label: "DeepSeek",
                      api_base_url: "https://api.deepseek.com/v1",
                      model: "deepseek-chat",
                    },
                    {
                      label: "通义千问",
                      api_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
                      model: "qwen-plus",
                    },
                    {
                      label: "Ollama 本地",
                      api_base_url: "http://localhost:11434/v1",
                      model: "llama3",
                    },
                  ].map((preset) => (
                    <Button
                      key={preset.label}
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!isAdmin}
                      onClick={() =>
                        setConsultForm((f) => ({
                          ...f,
                          api_base_url: preset.api_base_url,
                          model: preset.model,
                        }))
                      }
                    >
                      {preset.label}
                    </Button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Key 必须与所选服务商一致：OpenAI Key 不能用于 DeepSeek 地址，反之亦然。
                </p>
              </div>
              <div className="space-y-2">
                <Label>API Base URL</Label>
                <Input
                  placeholder="https://api.openai.com/v1"
                  disabled={!isAdmin}
                  value={consultForm.api_base_url}
                  onChange={(e) =>
                    setConsultForm((f) => ({ ...f, api_base_url: e.target.value }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  支持 OpenAI、Azure OpenAI、DeepSeek、Ollama 等兼容接口
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>模型名称</Label>
                  <Input
                    disabled={!isAdmin}
                    value={consultForm.model}
                    onChange={(e) => setConsultForm((f) => ({ ...f, model: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    disabled={!isAdmin}
                    placeholder={consultation?.api_key_configured ? "留空则不修改" : "仅粘贴 Key，如 sk-..."}
                    value={consultForm.api_key}
                    onChange={(e) => setConsultForm((f) => ({ ...f, api_key: e.target.value }))}
                  />
                  <p className="text-xs text-muted-foreground">
                    不要包含「Bearer」「密钥：」等前缀，Key 须为纯英文/数字
                  </p>
                </div>
              </div>
            </>
          )}

          <div className="space-y-3">
            <div className="space-y-2">
              <Label>系统提示词（内置预置）</Label>
              <p className="text-xs text-muted-foreground">
                5 套预置为系统固定模板，用于分阶段引导场景并生成架构方案；如需完全自定义请选择「自定义」。
              </p>
              <Select
                disabled={!isAdmin}
                value={consultForm.system_prompt_preset_id}
                onChange={(e) => {
                  const presetId = e.target.value as SystemPromptPresetId;
                  setConsultForm((f) => ({
                    ...f,
                    system_prompt_preset_id: presetId,
                  }));
                }}
              >
                {promptPresets.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.name}
                  </option>
                ))}
                <option value="custom">自定义</option>
              </Select>
            </div>

            {selectedPreset && !isCustomPrompt && (
              <div className="rounded-md border bg-muted/30 px-3 py-3 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-foreground">{selectedPreset.name}</p>
                  <span className="shrink-0 rounded bg-primary/10 px-2 py-0.5 text-[10px] text-primary">
                    内置固定
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">{selectedPreset.description}</p>
                <p className="mt-2 font-medium text-foreground">场景引导流程</p>
                <ol className="mt-1.5 space-y-1 text-muted-foreground">
                  {selectedPreset.guided_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </div>
            )}

            {isCustomPrompt && (
              <div className="space-y-2">
                <Label>自定义提示词</Label>
                <textarea
                  className="min-h-[140px] w-full rounded-md border bg-background px-3 py-2 text-sm"
                  disabled={!isAdmin}
                  placeholder={
                    "编写自定义系统提示词。建议包含分阶段场景引导，并要求 JSON 返回 " +
                    "reply、questions、ready_to_generate、scheme_summary 与 slots。"
                  }
                  value={consultForm.system_prompt}
                  onChange={(e) =>
                    setConsultForm((f) => ({ ...f, system_prompt: e.target.value }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  自定义模式可自行编写；内置 5 套预置不可修改，以保证场景引导与架构输出质量。
                </p>
              </div>
            )}
          </div>

          {consultMsg && <p className="text-sm text-green-600">{consultMsg}</p>}
          {consultErr && <p className="text-sm text-destructive">{consultErr}</p>}

          {isAdmin ? (
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={consultSaving}>
                {consultSaving ? "保存中…" : "保存咨询配置"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={consultTesting}
                onClick={() => void handleConsultationTest()}
              >
                {consultTesting ? "测试中…" : "测试连接"}
              </Button>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">仅管理员可修改咨询接口配置</p>
          )}
        </form>

        <form
          onSubmit={handlePasswordChange}
          className="space-y-4 rounded-xl border bg-card p-6 shadow-sm"
        >
          <h2 className="font-semibold">修改密码</h2>
          <div className="space-y-2">
            <Label htmlFor="current">当前密码</Label>
            <Input
              id="current"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new">新密码</Label>
            <Input
              id="new"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          {message && <p className="text-sm text-green-600">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={saving}>
            {saving ? "保存中…" : "更新密码"}
          </Button>
        </form>
      </div>
    </div>
  );
}
