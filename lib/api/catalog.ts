import type { Product } from '../types';
import { apiFetch, jsonPostInit } from './client';
import type { ProductRegistryItem } from './types';

export type ProductRegistryResponse = {
  ok: boolean;
  products: ProductRegistryItem[];
  growth_product_codes?: string[];
  feishu_product_codes?: string[];
  generated_at?: string;
};

export const catalogApi = {
  data: () => apiFetch<{ data: Product[] }>('/api/data', undefined, 'Failed to load data'),
  productRegistry: () =>
    apiFetch<ProductRegistryResponse>(
      '/api/product-registry',
      undefined,
      'Failed to load product registry'
    ),
  saveData: (data: Product[]) =>
    apiFetch<{ data: Product[] }>('/api/data', jsonPostInit({ data }), 'Failed to save data'),
  reset: () => apiFetch<{ data: Product[] }>('/api/reset', { method: 'POST' }, 'Failed to reset')
};
