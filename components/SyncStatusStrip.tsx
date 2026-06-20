'use client';

import type { SyncStatusResponse } from '@/lib/api/types';
import { formatUtcReadable } from '@/lib/utils';

const SOURCE_ORDER = ['reelfarm', 'museon_clone', 'growth_mixpanel'];

export function SyncStatusStrip({
  syncStatus,
  loading,
  onRefresh
}: {
  syncStatus: SyncStatusResponse | null;
  loading?: boolean;
  onRefresh: () => void | Promise<unknown>;
}) {
  const sources = syncStatus?.freshness?.sources || syncStatus?.sources || {};

  return (
    <div className="sync-status-strip">
      <div className="sync-status-items">
        {SOURCE_ORDER.map(source => {
          const item = sources[source] || {};
          const state = item.state || (item.status === 'success' ? 'fresh' : item.status ? 'error' : 'missing');
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
