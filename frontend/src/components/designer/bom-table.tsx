"use client";

import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCurrencyFull, formatNumber } from "@/lib/format";
import { useProjectStore } from "@/lib/stores/project-store";

const CATEGORY_LABELS: Record<string, string> = {
  GPU: "GPU",
  SWITCH: "交换机",
  OPTIC: "光模块",
  STORAGE: "存储",
  SOFTWARE: "软件",
  CPU: "CPU",
  MEM: "内存",
  INFRA: "基建",
};

export function BOMTable() {
  const bom = useProjectStore((s) => s.bom);
  const updateBomQuantity = useProjectStore((s) => s.updateBomQuantity);
  const total = bom.reduce((s, i) => s + i.total_price, 0);

  return (
    <div className="p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold">BOM 清单</h2>
        <p className="text-xs text-muted-foreground">调整数量后重新计算成本</p>
      </div>

      {bom.length === 0 ? (
        <div className="rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
          生成拓扑后自动填充 BOM
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="text-xs">品类</TableHead>
                <TableHead className="text-xs">型号</TableHead>
                <TableHead className="text-xs w-16">数量</TableHead>
                <TableHead className="text-xs text-right">单价</TableHead>
                <TableHead className="text-xs text-right">小计</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bom.map((item, index) => (
                <TableRow key={`${item.category}-${item.model}-${index}`}>
                  <TableCell className="py-2 text-xs font-medium">
                    {CATEGORY_LABELS[item.category] ?? item.category}
                  </TableCell>
                  <TableCell className="py-2 text-xs max-w-[100px] truncate" title={item.model}>
                    {item.model}
                  </TableCell>
                  <TableCell className="py-2">
                    <Input
                      type="number"
                      min={1}
                      className="h-7 w-14 text-xs px-1"
                      value={item.quantity}
                      onChange={(e) =>
                        updateBomQuantity(index, Number(e.target.value) || 1)
                      }
                    />
                  </TableCell>
                  <TableCell className="py-2 text-xs text-right text-muted-foreground">
                    {formatNumber(item.unit_price)}
                  </TableCell>
                  <TableCell className="py-2 text-xs text-right font-medium">
                    {formatNumber(item.total_price)}
                  </TableCell>
                </TableRow>
              ))}
              <TableRow className="bg-primary/5 font-semibold hover:bg-primary/5">
                <TableCell colSpan={4} className="py-2 text-xs text-right">
                  合计
                </TableCell>
                <TableCell className="py-2 text-xs text-right text-primary">
                  {formatCurrencyFull(total)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
