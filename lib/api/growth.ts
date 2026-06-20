import type { ProductGrowthPayload } from '../types';
import { apiFetch, jsonPostInit, withQuery } from './client';

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
    )
};
