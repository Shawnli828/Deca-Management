'use client';

import type { DatabaseSnapshot, ExternalApiKey } from '@/lib/types';
import { FormEvent, useState } from 'react';

export function DatabaseModal({
  open,
  snapshot,
  keys,
  generatedKey,
  onClose,
  onRefresh,
  onCreateKey,
  onRevokeKey,
  onCopy
}: {
  open: boolean;
  snapshot: DatabaseSnapshot | null;
  keys: ExternalApiKey[];
  generatedKey: string;
  onClose: () => void;
  onRefresh: () => void;
  onCreateKey: (name: string) => Promise<void>;
  onRevokeKey: (id: string) => void;
  onCopy: (value: string) => void;
}) {
  const [name, setName] = useState('');
  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onCreateKey(name || 'External AI');
    setName('');
  }

  return (
    <div className="database-modal is-open" onClick={event => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="database-panel" role="dialog" aria-modal="true" aria-labelledby="databaseTitle">
        <header className="database-header">
          <div>
            <h2 id="databaseTitle" className="database-title">数据库与外部 API</h2>
            <p className="database-subtitle">
              {snapshot ? `${snapshot.database_path || ''} · ${snapshot.table || ''} · 更新时间：${snapshot.updated_at || '暂无'}` : '不会自动读取完整数据库，需要时可手动加载。'}
            </p>
          </div>
          <button className="icon-btn" type="button" onClick={onClose} title="关闭">×</button>
        </header>
        <div className="database-body">
          <div className="database-stats">
            {snapshot?.stats ? Object.entries(snapshot.stats).map(([label, value]) => (
              <div className="database-stat" key={label}>
                <div className="database-stat-label">{label}</div>
                <div className="database-stat-value">{value}</div>
              </div>
            )) : null}
          </div>
          <div className="database-actions">
            <button className="btn ghost" type="button" onClick={onRefresh}>读取数据库视图</button>
            <button className="btn ghost" type="button" onClick={() => snapshot?.data && onCopy(JSON.stringify(snapshot.data, null, 2))}>复制 JSON</button>
          </div>
          <section className="api-key-panel">
            <div className="api-key-head">
              <div>
                <h3>外部 AI API Keys</h3>
                <p>生成后给其他 AI 使用 Bearer Token 读取素材数据。</p>
              </div>
              <form className="api-key-form" onSubmit={submit}>
                <input className="text-input" value={name} onChange={event => setName(event.target.value)} type="text" placeholder="Key 名称，例如 AI Classifier" />
                <button className="btn primary" type="submit">生成 Key</button>
              </form>
            </div>
            <div className="generated-api-key">
              {generatedKey ? (
                <>
                  <div className="generated-api-key-label">新 Key 只显示一次，请现在复制给外部 AI。</div>
                  <code>{generatedKey}</code>
                  <button className="btn ghost" type="button" onClick={() => onCopy(generatedKey)}>复制</button>
                </>
              ) : null}
            </div>
            <div className="api-key-list">
              {keys.length ? keys.map(key => (
                <div className={`api-key-row ${key.active ? '' : 'is-revoked'}`} key={key.id}>
                  <div>
                    <div className="api-key-name">{key.name || 'External AI'}</div>
                    <div className="api-key-meta">{key.prefix || 'deca_...'} · {(key.permissions || []).join(', ') || '无权限'} · {key.active ? 'active' : 'revoked'}</div>
                  </div>
                  {key.active ? <button className="btn danger" type="button" onClick={() => onRevokeKey(key.id)}>停用</button> : <span className="item-meta">已停用</span>}
                </div>
              )) : <div className="item-meta">还没有外部 API Key。</div>}
            </div>
          </section>
          <pre className="database-json">{snapshot?.data ? JSON.stringify(snapshot.data, null, 2) : '数据库 JSON 暂未加载。'}</pre>
        </div>
      </section>
    </div>
  );
}
