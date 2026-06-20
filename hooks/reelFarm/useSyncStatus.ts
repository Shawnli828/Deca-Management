import { useCallback, useState } from 'react';
import { api } from '@/lib/api';
import type { SyncStatusResponse } from '@/lib/api/types';

export function useSyncStatus() {
  const [syncStatus, setSyncStatus] = useState<SyncStatusResponse | null>(null);
  const [syncStatusLoading, setSyncStatusLoading] = useState(false);

  const loadSyncStatus = useCallback(async () => {
    setSyncStatusLoading(true);
    try {
      const payload = await api.getSyncStatus();
      setSyncStatus(payload);
      return payload;
    } finally {
      setSyncStatusLoading(false);
    }
  }, []);

  return {
    syncStatus,
    syncStatusLoading,
    loadSyncStatus
  };
}
