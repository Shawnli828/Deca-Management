import { apiFetch, jsonPostInit } from './client';
import type { MuseonSyncCountryResponse, ReelfarmSyncCountryResponse } from './types';

export const syncApi = {
  syncCountry: (payload: Record<string, unknown>) =>
    apiFetch<ReelfarmSyncCountryResponse>(
      '/api/reelfarm/sync-country',
      jsonPostInit(payload),
      'Failed to sync ReelFarm country'
    ),
  syncMuseonCloneCountry: (payload: Record<string, unknown>) =>
    apiFetch<MuseonSyncCountryResponse>(
      '/api/museon/sync-country',
      jsonPostInit(payload),
      'Failed to sync Museon clone country'
    )
};
