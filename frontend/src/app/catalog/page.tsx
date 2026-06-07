"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Package, Pencil, Plus, Search, Sparkles, Trash2, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { SkuFormDialog } from "@/components/catalog/sku-form-dialog";
import { MainNav } from "@/components/layout/main-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  aiSuggestSkus,
  batchImportSkus,
  createSku,
  deleteSku,
  listSkus,
  updateSku,
  type SKUPayload,
} from "@/lib/api/catalog";
import { formatNumber } from "@/lib/format";
import type { SKUCatalog, SKUCategory } from "@/types";

const CATEGORY_LABELS: Record<string, string> = {
  GPU: "GPU",
  CPU: "CPU",
  MEM: "内存",
  SWITCH: "交换机",
  OPTIC: "光模块",
  STORAGE: "存储",
  SOFTWARE: "软件",
  INFRA: "基建",
};

const SAMPLE_IMPORT = `[
  {
    "category": "GPU",
    "vendor": "NVIDIA",
    "model": "H200 141G",
    "specs_json": {"memory_gb": 141},
    "base_price": "320000",
    "channel_price": "300000",
    "cost_dimension": "COMPUTE"
  }
]`;

export default function CatalogPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("ALL");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<SKUCatalog | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState(SAMPLE_IMPORT);
  const [importError, setImportError] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const [aiQuery, setAiQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [aiResult, setAiResult] = useState<Awaited<ReturnType<typeof aiSuggestSkus>> | null>(
    null
  );

  const { data, isLoading, error } = useQuery({
    queryKey: ["skus", category, search, page],
    queryFn: () =>
      listSkus(
        category === "ALL" ? undefined : (category as SKUCategory),
        page,
        20,
        search
      ),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["skus"] });
    queryClient.invalidateQueries({ queryKey: ["skus-count"] });
  };

  const deleteMutation = useMutation({
    mutationFn: deleteSku,
    onSuccess: invalidate,
  });

  const importMutation = useMutation({
    mutationFn: (items: SKUPayload[]) => batchImportSkus(items),
    onSuccess: () => {
      invalidate();
      setImportOpen(false);
    },
  });

  const totalPages = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, Math.ceil(data.total / data.page_size));
  }, [data]);

  async function handleSave(payload: SKUPayload) {
    if (editing) {
      await updateSku(editing.id, payload);
    } else {
      await createSku(payload);
    }
    invalidate();
  }

  async function handleImport() {
    setImportError("");
    try {
      const items = JSON.parse(importText) as SKUPayload[];
      if (!Array.isArray(items) || items.length === 0) {
        setImportError("请提供至少一条 SKU 记录");
        return;
      }
      await importMutation.mutateAsync(items);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "导入失败，请检查 JSON 格式");
    }
  }

  async function handleAiSearch(importToCatalog: boolean) {
    setAiError("");
    setAiLoading(true);
    try {
      const text = aiQuery.trim();
      if (text.length < 3) {
        setAiError("请至少输入 3 个字的检索需求");
        return;
      }
      const result = await aiSuggestSkus({
        requirement: text,
        import_to_catalog: importToCatalog,
      });
      setAiResult(result);
      if (importToCatalog) {
        invalidate();
      }
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "AI 检索失败");
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav showNewProject />

      <div className="mx-auto max-w-[1200px] px-6 py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="mb-1 flex items-center gap-2 text-primary">
              <Package className="h-5 w-5" />
              <span className="text-sm font-medium">硬件目录</span>
            </div>
            <h1 className="text-2xl font-bold">SKU 库管理</h1>
            <p className="mt-1 text-muted-foreground">
              灵活维护硬件与软件 SKU，支持增删改查与批量导入；系统已预置 60+ 条权威厂商规格作为默认目录
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setAiResult(null);
                setAiError("");
                setAiOpen(true);
              }}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              AI 搜索补全
            </Button>
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <Upload className="mr-2 h-4 w-4" />
              批量导入
            </Button>
            <Button
              onClick={() => {
                setEditing(null);
                setDialogOpen(true);
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              新增 SKU
            </Button>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap gap-3">
          <div className="relative min-w-[220px] flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索型号、厂商…"
              className="pl-9"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <Select
            className="w-[160px]"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="ALL">全部品类</option>
            {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : "加载失败"}
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead>品类</TableHead>
                  <TableHead>厂商</TableHead>
                  <TableHead>型号</TableHead>
                  <TableHead className="text-right">指导价</TableHead>
                  <TableHead className="text-right">渠道价</TableHead>
                  <TableHead>成本维度</TableHead>
                  <TableHead className="w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((sku) => (
                  <TableRow key={sku.id}>
                    <TableCell>
                      <Badge variant="secondary">
                        {CATEGORY_LABELS[sku.category] ?? sku.category}
                      </Badge>
                    </TableCell>
                    <TableCell>{sku.vendor}</TableCell>
                    <TableCell className="font-medium">{sku.model}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      ¥ {formatNumber(Number(sku.base_price))}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {sku.channel_price
                        ? `¥ ${formatNumber(Number(sku.channel_price))}`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {sku.cost_dimension}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditing(sku);
                            setDialogOpen(true);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            if (confirm(`确定删除 ${sku.model}？`)) {
                              deleteMutation.mutate(sku.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="flex items-center justify-between border-t px-4 py-3 text-sm text-muted-foreground">
              <span>
                共 {data?.total ?? 0} 条 · 第 {page} / {totalPages} 页
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  上一页
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  下一页
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      <SkuFormDialog
        open={dialogOpen}
        initial={editing}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSave}
      />

      {aiOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-card p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold">AI 搜索补全 SKU</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              描述算力/网络/存储需求，系统将结合网络检索与 LLM 推荐可入库的 SKU（需在设置中配置 API Key 以获得更精准结果）
            </p>
            <textarea
              className="min-h-[100px] w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="例如：64 卡 H800 训推混合集群，32 口 400G 交换机，等保三级…"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
            />
            {aiError && <p className="mt-2 text-sm text-destructive">{aiError}</p>}
            {aiResult && (
              <div className="mt-4 space-y-2 rounded-md border bg-muted/30 p-3 text-sm">
                <p className="text-muted-foreground">{aiResult.note}</p>
                <ul className="max-h-48 space-y-2 overflow-y-auto text-xs">
                  {aiResult.items.map((item, i) => (
                    <li key={i} className="rounded border bg-background p-2">
                      <span className="font-medium">
                        [{item.category}] {item.vendor} {item.model}
                      </span>
                      <span className="ml-2 text-muted-foreground">¥ {item.base_price}</span>
                      {item.rationale && (
                        <p className="mt-1 text-muted-foreground">{item.rationale}</p>
                      )}
                    </li>
                  ))}
                </ul>
                {aiResult.imported.length > 0 && (
                  <p className="text-green-700">已入库 {aiResult.imported.length} 条新品类</p>
                )}
              </div>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setAiOpen(false)}>
                关闭
              </Button>
              <Button
                variant="outline"
                disabled={aiLoading}
                onClick={() => void handleAiSearch(false)}
              >
                {aiLoading ? "检索中…" : "仅预览建议"}
              </Button>
              <Button disabled={aiLoading} onClick={() => void handleAiSearch(true)}>
                {aiLoading ? "检索中…" : "检索并入库"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {importOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-card p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold">批量导入 SKU</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              粘贴 JSON 数组，字段与新增 SKU 表单一致
            </p>
            <textarea
              className="min-h-[240px] w-full rounded-md border bg-background px-3 py-2 font-mono text-sm"
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
            />
            {importError && <p className="mt-2 text-sm text-destructive">{importError}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setImportOpen(false)}>
                取消
              </Button>
              <Button onClick={handleImport} disabled={importMutation.isPending}>
                {importMutation.isPending ? "导入中…" : "确认导入"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
