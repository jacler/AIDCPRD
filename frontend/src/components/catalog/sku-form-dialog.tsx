"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { SKUPayload } from "@/lib/api/catalog";
import type { CostDimension, SKUCatalog, SKUCategory } from "@/types";

const CATEGORIES: SKUCategory[] = [
  "GPU",
  "CPU",
  "MEM",
  "SWITCH",
  "OPTIC",
  "STORAGE",
  "SOFTWARE",
  "INFRA",
];

const DIMENSIONS: CostDimension[] = [
  "COMPUTE",
  "NETWORK",
  "STORAGE",
  "SOFTWARE",
  "INFRA",
];

const EMPTY: SKUPayload = {
  category: "GPU",
  vendor: "",
  model: "",
  specs_json: {},
  base_price: "",
  channel_price: "",
  cost_dimension: "COMPUTE",
};

interface SkuFormDialogProps {
  open: boolean;
  initial?: SKUCatalog | null;
  onClose: () => void;
  onSubmit: (payload: SKUPayload) => Promise<void>;
}

export function SkuFormDialog({ open, initial, onClose, onSubmit }: SkuFormDialogProps) {
  const [form, setForm] = useState<SKUPayload>(EMPTY);
  const [specsText, setSpecsText] = useState("{}");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        category: initial.category,
        vendor: initial.vendor,
        model: initial.model,
        specs_json: initial.specs_json,
        base_price: initial.base_price,
        channel_price: initial.channel_price ?? "",
        cost_dimension: initial.cost_dimension,
      });
      setSpecsText(JSON.stringify(initial.specs_json ?? {}, null, 2));
    } else {
      setForm(EMPTY);
      setSpecsText("{}");
    }
    setError("");
  }, [open, initial]);

  if (!open) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    let specs_json: Record<string, unknown> = {};
    try {
      specs_json = specsText.trim() ? JSON.parse(specsText) : {};
    } catch {
      setError("规格 JSON 格式不正确");
      return;
    }
    setSaving(true);
    try {
      await onSubmit({
        ...form,
        specs_json,
        channel_price: form.channel_price === "" ? null : form.channel_price,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border bg-card p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">{initial ? "编辑 SKU" : "新增 SKU"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>品类</Label>
              <Select
                value={form.category}
                onChange={(e) =>
                  setForm((f) => ({ ...f, category: e.target.value as SKUCategory }))
                }
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label>成本维度</Label>
              <Select
                value={form.cost_dimension}
                onChange={(e) =>
                  setForm((f) => ({ ...f, cost_dimension: e.target.value as CostDimension }))
                }
              >
                {DIMENSIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>厂商</Label>
            <Input
              value={form.vendor}
              onChange={(e) => setForm((f) => ({ ...f, vendor: e.target.value }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label>型号</Label>
            <Input
              value={form.model}
              onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>指导价 (¥)</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={form.base_price}
                onChange={(e) => setForm((f) => ({ ...f, base_price: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>渠道价 (¥)</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={form.channel_price ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, channel_price: e.target.value }))}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>规格 JSON</Label>
            <textarea
              className="min-h-[100px] w-full rounded-md border bg-background px-3 py-2 font-mono text-sm"
              value={specsText}
              onChange={(e) => setSpecsText(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              取消
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "保存中…" : "保存"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
