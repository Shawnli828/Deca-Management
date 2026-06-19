'use client';

import type { DatabaseSnapshot, ExternalApiKey } from '@/lib/types';
import { useState } from 'react';
import { ApiKeyPanel } from './ApiKeyPanel';
import { DataApiReference } from './DataApiReference';

type DatabaseTab = 'keys' | 'docs';

export function DatabaseModal({
  open,
  keys,
  generatedKey,
  onClose,
  onCreateKey,
  onRevokeKey,
  onCopy
}: {
  open: boolean;
  snapshot?: DatabaseSnapshot | null;
  keys: ExternalApiKey[];
  generatedKey: string;
  onClose: () => void;
  onRefresh?: () => void;
  onCreateKey: (name: string) => Promise<void>;
  onRevokeKey: (id: string) => void;
  onCopy: (value: string) => void;
}) {
  const [tab, setTab] = useState<DatabaseTab>('keys');
  if (!open) return null;

  return (
    <div
      className="database-modal is-open"
      onClick={event => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="database-panel" role="dialog" aria-modal="true" aria-labelledby="databaseTitle">
        <header className="database-header">
          <div>
            <h2 id="databaseTitle" className="database-title">API Key</h2>
            <p className="database-subtitle">生成 Bearer Token，给外部工具读取中台素材数据。</p>
          </div>
          <button className="icon-btn" type="button" onClick={onClose} title="关闭">×</button>
        </header>
        <div className="database-body">
          <div className="api-modal-tabs">
            <button className={tab === 'keys' ? 'active' : ''} type="button" onClick={() => setTab('keys')}>API Keys</button>
            <button className={tab === 'docs' ? 'active' : ''} type="button" onClick={() => setTab('docs')}>API 使用说明</button>
          </div>
          {tab === 'keys' ? (
            <ApiKeyPanel
              keys={keys}
              generatedKey={generatedKey}
              onCreateKey={onCreateKey}
              onRevokeKey={onRevokeKey}
              onCopy={onCopy}
            />
          ) : (
            <DataApiReference onCopy={onCopy} />
          )}
        </div>
      </section>
    </div>
  );
}
