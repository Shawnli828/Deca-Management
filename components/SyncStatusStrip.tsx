'use client';

import type { SyncStatusResponse } from '@/lib/api/types';
import { SYNC_STATUS_SOURCE_ORDER, syncStatusPillState, syncStatusSources } from '@/lib/domain/syncStatus';
import { formatUtcReadable } from '@/lib/utils';

export function SyncStatusStrip({
  syncStatus,
  loading,
  onRefresh
}: {
  syncStatus: SyncStatusResponse | null;
  loading?: boolean;
  onRefresh: () => void | Promise<unknown>;
}) {
  const sources = syncStatusSources(syncStatus);

  return (
    <div className="sync-status-strip">
      <div className="sync-status-items">
        {SYNC_STATUS_SOURCE_ORDER.map(source => {
          const item = sources[source] || {};
          const state = syncStatusPillState(item);
          return (
            <span className={`sync-status-pill ${state}`} key={source}>
              <b>{item.label || source}</b>
              <small>{item.last_finished_at ? formatUtcReadable(item.last_finished_at) : '暂无记录'}</small>
            </span>
          );
        })}
      </div>
      <button className="btn ghost sync-status-refresh" type="button" onClick={onRefresh} disabled={loading}>
        {loading ? 'Checking...' : '同步状态'}
      </button>
    </div>
  );
}
