import type { Product } from '../types';
import { apiFetch, jsonPostInit } from './client';

export const catalogApi = {
  data: () => apiFetch<{ data: Product[] }>('/api/data', undefined, 'Failed to load data'),
  saveData: (data: Product[]) =>
    apiFetch<{ data: Product[] }>('/api/data', jsonPostInit({ data }), 'Failed to save data'),
  reset: () => apiFetch<{ data: Product[] }>('/api/reset', { method: 'POST' }, 'Failed to reset')
};
