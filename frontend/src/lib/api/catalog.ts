import { apiFetch } from "@/lib/api-client";
import type {
  CostDimension,
  PaginatedResponse,
  SKUCatalog,
  SKUCategory,
} from "@/types";

export interface SKUPayload {
  category: SKUCategory;
  vendor: string;
  model: string;
  specs_json?: Record<string, unknown>;
  base_price: number | string;
  channel_price?: number | string | null;
  cost_dimension: CostDimension;
}

export interface SkuAiSuggestItem {
  category: string;
  vendor: string;
  model: string;
  specs_json?: Record<string, unknown>;
  base_price: string;
  channel_price?: string | null;
  cost_dimension: string;
  rationale?: string;
}

export interface SkuAiSuggestResponse {
  items: SkuAiSuggestItem[];
  imported: SKUCatalog[];
  skipped: SKUCatalog[];
  note: string;
  engine: string;
}

export async function listSkus(
  category?: SKUCategory,
  page = 1,
  pageSize = 50,
  search?: string
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (category) params.set("category", category);
  if (search?.trim()) params.set("search", search.trim());
  return apiFetch<PaginatedResponse<SKUCatalog>>(
    `/api/v1/catalog/skus?${params.toString()}`
  );
}

export async function getSku(skuId: string) {
  return apiFetch<SKUCatalog>(`/api/v1/catalog/skus/${skuId}`);
}

export async function createSku(payload: SKUPayload) {
  return apiFetch<SKUCatalog>("/api/v1/catalog/skus", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSku(skuId: string, payload: Partial<SKUPayload>) {
  return apiFetch<SKUCatalog>(`/api/v1/catalog/skus/${skuId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteSku(skuId: string) {
  return apiFetch<void>(`/api/v1/catalog/skus/${skuId}`, { method: "DELETE" });
}

export async function batchImportSkus(items: SKUPayload[]) {
  return apiFetch<SKUCatalog[]>("/api/v1/catalog/skus/batch-import", {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}

export async function listSkuCategories() {
  return apiFetch<{ value: string; label: string }[]>("/api/v1/catalog/categories");
}

export async function aiSuggestSkus(payload: {
  requirement: string;
  extracted?: Record<string, unknown>;
  import_to_catalog?: boolean;
}) {
  return apiFetch<SkuAiSuggestResponse>("/api/v1/catalog/skus/ai-suggest", {
    method: "POST",
    body: JSON.stringify({
      requirement: payload.requirement,
      extracted: payload.extracted ?? null,
      import_to_catalog: payload.import_to_catalog ?? true,
    }),
  });
}
