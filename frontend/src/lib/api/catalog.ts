import { apiFetch } from "@/lib/api-client";
import type { PaginatedResponse, SKUCatalog, SKUCategory } from "@/types";

export async function listSkus(category?: SKUCategory, page = 1, pageSize = 50) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (category) params.set("category", category);
  return apiFetch<PaginatedResponse<SKUCatalog>>(
    `/api/v1/catalog/skus?${params.toString()}`
  );
}
