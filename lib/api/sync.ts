import { apiFetch, jsonPostInit } from './client';
import type {
  MuseonSyncCountryResponse,
  ReelfarmSyncCountryResponse,
  SyncResultResponse,
  SyncStatusResponse
} from './types';

export const syncApi = {
  getSyncStatus: () =>
    apiFetch<SyncStatusResponse>(
      '/api/sync/status',
      undefined,
      'Failed to load sync status'
    ),
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
    ),
  syncReelfarmAll: () =>
    apiFetch<SyncResultResponse>(
      '/api/reelfarm/sync-all',
      { method: 'POST' },
      'Failed to sync all ReelFarm records'
    ),
  syncMuseonAll: () =>
    apiFetch<SyncResultResponse>(
      '/api/museon/sync-all',
      { method: 'POST' },
      'Failed to sync all Museon records'
    )
};
