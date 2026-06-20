import { apiFetch, jsonPostInit } from './client';

export const syncApi = {
  syncCountry: (payload: Record<string, unknown>) =>
    apiFetch<{ ok: boolean; creator_count: number; material_count: number; synced_at?: string }>(
      '/api/reelfarm/sync-country',
      jsonPostInit(payload),
      'Failed to sync ReelFarm country'
    ),
  syncMuseonCloneCountry: (payload: Record<string, unknown>) =>
    apiFetch<{ ok: boolean; skipped?: boolean; creator_count: number; material_count: number; post_count?: number; synced_at?: string }>(
      '/api/museon/sync-country',
      jsonPostInit(payload),
      'Failed to sync Museon clone country'
    )
};
