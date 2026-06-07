"use client";

import Link from "next/link";
import { Loader2, MessageSquare, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  clearStoredSessionId,
  isValidProjectId,
  loadStoredMessages,
  loadStoredSessionId,
  storeMessages,
  storeSessionId,
  streamConsultationMessage,
} from "@/lib/api/consultation";
import type { ConsultationMessage, ExtractedRequirements } from "@/lib/api/consultation";
import { getConsultationSettings } from "@/lib/api/settings";

interface RequirementChatProps {
  projectId?: string;
  onApply?: (extracted: ExtractedRequirements) => void;
  onApplyPlan?: (extracted: ExtractedRequirements) => Promise<void>;
  onApplyAndGenerate?: (extracted: ExtractedRequirements) => void | Promise<void>;
  compact?: boolean;
}

export function RequirementChat({
  projectId,
  onApply,
  onApplyPlan,
  onApplyAndGenerate,
  compact = false,
}: RequirementChatProps) {
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ConsultationMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [extracted, setExtracted] = useState<ExtractedRequirements | null>(null);
  const [engine, setEngine] = useState<"rule" | "openai_compatible">("rule");
  const [providerConfigured, setProviderConfigured] = useState<"rule" | "openai_compatible">("rule");
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [expanded, setExpanded] = useState(!compact);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streamingText, loading]);

  useEffect(() => {
    void getConsultationSettings()
      .then((s) => {
        setProviderConfigured(s.provider);
        setApiKeyConfigured(s.api_key_configured);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    abortRef.current?.abort();
    setSessionId(loadStoredSessionId(projectId));
    setMessages(loadStoredMessages(projectId));
    setExtracted(null);
    setStreamingText("");
  }, [projectId]);

  async function handleSend(e?: FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setLoading(true);
    setInput("");
    setStreamingText("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await streamConsultationMessage({
        message: text,
        sessionId,
        projectId,
        signal: controller.signal,
        onToken: (delta) => {
          setStreamingText((prev) => prev + delta);
        },
      });

      setSessionId(res.session_id);
      storeSessionId(projectId, res.session_id);
      setMessages(res.messages);
      storeMessages(projectId, res.messages);
      setExtracted(res.extracted);
      setEngine(res.engine);
      setStreamingText("");
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "咨询失败，请重试",
        },
      ]);
      setStreamingText("");
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function handleClearHistory() {
    abortRef.current?.abort();
    clearStoredSessionId(projectId);
    setSessionId(undefined);
    setMessages([]);
    setExtracted(null);
    setStreamingText("");
  }

  async function handleApply(generateTopology: boolean) {
    if (!extracted) return;
    setApplying(true);
    setApplyError(null);
    setApplySuccess(null);
    try {
      if (onApplyPlan) {
        await onApplyPlan(extracted);
        return;
      }
      if (generateTopology && onApplyAndGenerate) {
        await onApplyAndGenerate(extracted);
        setApplySuccess("方案已应用，拓扑与 BOM 已更新");
      } else if (onApply) {
        onApply(extracted);
        setApplySuccess("方案参数已填入表单");
      }
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "应用方案失败");
    } finally {
      setApplying(false);
    }
  }

  const canApply = !!(onApplyPlan || onApply || onApplyAndGenerate);
  const applyLabel = onApplyPlan
    ? applying
      ? "创建并生成中…"
      : "创建项目并生成方案"
    : onApplyAndGenerate
      ? applying
        ? "生成中…"
        : "应用方案并生成拓扑"
      : applying
        ? "应用中…"
        : "应用方案参数";

  const usingRuleFallback =
    providerConfigured === "openai_compatible" && !apiKeyConfigured && engine === "rule";

  if (compact && !expanded) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={() => setExpanded(true)}
      >
        <Sparkles className="mr-2 h-4 w-4" />
        用自然语言描述需求
      </Button>
    );
  }

  return (
    <div
      className={
        compact
          ? "flex min-h-[280px] max-h-[min(55vh,520px)] flex-col border-b"
          : "flex max-h-[min(70vh,640px)] flex-col rounded-xl border bg-card shadow-sm"
      }
    >
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <MessageSquare className="h-4 w-4 text-primary" />
          智能需求咨询
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] ${
              engine === "openai_compatible"
                ? "bg-green-100 text-green-800"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {engine === "openai_compatible" ? "LLM" : "规则引擎"}
          </span>
          {messages.length > 0 && (
            <button
              type="button"
              className="text-[10px] text-muted-foreground hover:text-foreground"
              onClick={handleClearHistory}
            >
              清空
            </button>
          )}
          {compact && (
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setExpanded(false)}
            >
              收起
            </button>
          )}
        </div>
      </div>

      {isValidProjectId(projectId) && (
        <div className="border-b bg-muted/20 px-3 py-1 text-[10px] text-muted-foreground">
          会话独立绑定当前项目，不同项目不共享对话记忆
        </div>
      )}

      {usingRuleFallback && (
        <div className="border-b bg-amber-50 px-3 py-2 text-[11px] text-amber-900">
          已在设置中选择 LLM 模式但未配置 API Key，当前为模板回复。
          <Link href="/settings" className="ml-1 underline">
            去设置 API Key
          </Link>
        </div>
      )}

      <div
        ref={messagesContainerRef}
        className={`min-h-0 flex-1 space-y-2 overflow-y-auto overflow-x-hidden px-3 py-2 ${
          compact ? "" : ""
        }`}
      >
        {messages.length === 0 && !streamingText && (
          <p className="text-xs text-muted-foreground leading-relaxed">
            例如：「为医院提供 10P 算力，用于 CT 影像 AI 辅助诊断」——我会追问场景、合规等细节，并给出可落地的集群方案参数。
            {providerConfigured === "rule" && (
              <>
                {" "}
                管理员可在
                <Link href="/settings" className="text-primary underline">
                  设置
                </Link>
                中配置 LLM API Key 以获得更智能的个性化回答。
              </>
            )}
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`rounded-lg px-2.5 py-2 text-sm leading-relaxed break-words whitespace-pre-wrap ${
              msg.role === "user"
                ? "ml-4 bg-primary/10 text-foreground"
                : "mr-4 bg-muted text-foreground"
            }`}
          >
            {msg.content}
          </div>
        ))}
        {streamingText && (
          <div className="mr-4 rounded-lg bg-muted px-2.5 py-2 text-sm leading-relaxed break-words whitespace-pre-wrap text-foreground">
            {streamingText}
            <span className="ml-0.5 inline-block h-3.5 w-1 animate-pulse bg-primary/60 align-middle" />
          </div>
        )}
        {loading && !streamingText && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            分析中…
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="flex gap-2 border-t p-2">
        <input
          className="flex-1 rounded-md border bg-background px-2 py-1.5 text-xs"
          placeholder="描述算力需求、行业场景…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <Button type="submit" size="sm" disabled={loading || !input.trim()}>
          发送
        </Button>
      </form>

      {extracted && canApply && (
        <div className="shrink-0 space-y-2 border-t p-2">
          {extracted.scheme_summary && (
            <div className="rounded-md bg-primary/5 px-2.5 py-2 text-xs leading-relaxed break-words text-foreground">
              <span className="font-medium">推荐方案：</span>
              {extracted.scheme_summary}
            </div>
          )}
          <div className="grid grid-cols-2 gap-1 text-[10px] text-muted-foreground">
            {extracted.target_gpus && <span>GPU {extracted.target_gpus} 张</span>}
            {extracted.scenario && <span>场景 {extracted.scenario}</span>}
            {extracted.gpus_per_node && <span>{extracted.gpus_per_node} 卡/节点</span>}
            {extracted.switch_ports && <span>{extracted.switch_ports} 口交换机</span>}
          </div>
          {applyError && (
            <p className="text-[11px] text-destructive">{applyError}</p>
          )}
          {applySuccess && (
            <p className="text-[11px] text-green-700">{applySuccess}</p>
          )}
          <Button
            size="sm"
            className="w-full"
            disabled={applying}
            onClick={() =>
              void handleApply(!!onApplyAndGenerate && !onApplyPlan)
            }
          >
            <Sparkles className="mr-2 h-4 w-4" />
            {applyLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
