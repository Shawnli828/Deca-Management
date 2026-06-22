import type { ProductGrowthPayload } from '../types';
import { apiFetch, jsonPostInit, withQuery } from './client';

export type GrowthProductsSyncPayload = {
  ok: boolean;
  records?: Array<{ product_code?: string; count?: number }>;
  errors?: Array<{ product_code?: string; error?: string; message?: string }>;
  error_count?: number;
  synced_count?: number;
  finished_at?: string;
};

export const growthApi = {
  productGrowth: (productCode: string, days = 30) =>
    apiFetch<ProductGrowthPayload>(
      withQuery('/api/growth', new URLSearchParams({ product_code: productCode, days: String(days) })),
      undefined,
      'Failed to load growth dashboard'
    ),
  syncProductGrowth: (productCode: string, days = 30) =>
    apiFetch<{ ok: boolean; count: number; records: ProductGrowthPayload['series'] }>(
      '/api/growth/sync-product',
      jsonPostInit({ product_code: productCode, days }),
      'Failed to sync growth snapshots'
    ),
  syncProductsGrowth: (productCodes: readonly string[], days = 30) =>
    apiFetch<GrowthProductsSyncPayload>(
      '/api/growth/sync-products',
      jsonPostInit({ product_codes: productCodes, days }),
      'Failed to sync growth snapshots'
    )
};
