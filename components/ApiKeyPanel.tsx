'use client';

import type { ExternalApiKey } from '@/lib/types';
import { FormEvent, useState } from 'react';

export function ApiKeyPanel({
  keys,
  generatedKey,
  onCreateKey,
  onRevokeKey,
  onCopy
}: {
  keys: ExternalApiKey[];
  generatedKey: string;
  onCreateKey: (name: string) => Promise<void>;
  onRevokeKey: (id: string) => void;
  onCopy: (value: string) => void;
}) {
  const [name, setName] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onCreateKey(name || 'API Key');
    setName('');
  }

  return (
    <section className="api-key-panel">
      <div className="api-key-head">
        <div>
          <h3>API Keys</h3>
          <p>使用方式：在请求头加入 Authorization: Bearer deca_...</p>
        </div>
        <form className="api-key-form" onSubmit={submit}>
          <input className="text-input" value={name} onChange={event => setName(event.target.value)} type="text" placeholder="Key 名称，例如 Classifier" />
          <button className="btn primary" type="submit">生成 Key</button>
        </form>
      </div>
      <div className="generated-api-key">
        {generatedKey ? (
          <>
            <div className="generated-api-key-label">新 Key 只显示一次，请现在复制。</div>
            <code>{generatedKey}</code>
            <button className="btn ghost" type="button" onClick={() => onCopy(generatedKey)}>复制</button>
          </>
        ) : null}
      </div>
      <div className="api-key-list">
        {keys.length ? keys.map(key => (
          <div className={`api-key-row ${key.active ? '' : 'is-revoked'}`} key={key.id}>
            <div>
              <div className="api-key-name">{key.name || 'API Key'}</div>
              <div className="api-key-meta">{key.prefix || 'deca_...'} · {(key.permissions || []).join(', ') || '无权限'} · {key.active ? 'active' : 'revoked'}</div>
            </div>
            {key.active ? <button className="btn danger" type="button" onClick={() => onRevokeKey(key.id)}>停用</button> : <span className="item-meta">已停用</span>}
          </div>
        )) : <div className="item-meta">还没有 API Key。</div>}
      </div>
    </section>
  );
}
