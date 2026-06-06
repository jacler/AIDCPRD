"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2, Package, Search } from "lucide-react";

import { MainNav } from "@/components/layout/main-nav";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listSkus } from "@/lib/api/catalog";
import { formatNumber } from "@/lib/format";
import { useMemo, useState } from "react";

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

export default function CatalogPage() {
  const [search, setSearch] = useState("");
  const { data, isLoading, error } = useQuery({
    queryKey: ["skus"],
    queryFn: () => listSkus(undefined, 1, 100),
  });

  const filtered = useMemo(() => {
    const items = data?.items ?? [];
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter(
      (sku) =>
        sku.model.toLowerCase().includes(q) ||
        sku.vendor.toLowerCase().includes(q) ||
        sku.category.toLowerCase().includes(q)
    );
  }, [data?.items, search]);

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
            <h1 className="text-2xl font-bold">SKU 库</h1>
            <p className="mt-1 text-muted-foreground">
              硬件与软件 SKU 价格表，用于 BOM 自动匹配与成本计算
            </p>
          </div>
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索型号、厂商…"
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">加载失败，请确认后端已启动</p>
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
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((sku) => (
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="flex items-center justify-between border-t px-4 py-3 text-sm text-muted-foreground">
              <span>
                显示 {filtered.length} / {data?.total ?? 0} 条 SKU
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
