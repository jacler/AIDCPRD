import type { PreliminaryBOMItem } from "@/types";

export function exportBomToCsv(
  bom: PreliminaryBOMItem[],
  projectName: string
): void {
  const headers = ["品类", "型号", "数量", "单价", "小计", "成本维度"];
  const rows = bom.map((item) => [
    item.category,
    item.model,
    String(item.quantity),
    String(item.unit_price),
    String(item.total_price),
    item.cost_dimension,
  ]);
  const total = bom.reduce((s, i) => s + i.total_price, 0);
  rows.push(["合计", "", "", "", String(total), ""]);

  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${projectName}-BOM.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
