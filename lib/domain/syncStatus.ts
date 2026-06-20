import type { SyncFreshnessSource, SyncStatusResponse } from '@/lib/api/types';

export const SYNC_STATUS_SOURCE_ORDER = ['reelfarm', 'museon_clone', 'growth_mixpanel'] as const;

export function syncStatusSources(syncStatus: SyncStatusResponse | null) {
  return syncStatus?.freshness?.sources || syncStatus?.sources || {};
}

export function syncStatusPillState(item: SyncFreshnessSource | undefined) {
  if (!item) return 'missing';
  return item.state || (item.status === 'success' ? 'fresh' : item.status ? 'error' : 'missing');
}
