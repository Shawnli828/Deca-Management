'use client';

import type { ExternalApiKey } from '@/lib/types';
import { FormEvent, useState } from 'react';

export function ApiKeyPage({
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

  const example = `curl "https://deca-management.vercel.app/api/data/query?resource=summary" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`;

  return (
    <section className="api-key-page">
      <header className="api-key-page-head">
        <div>
          <h1>API Key</h1>
          <p>给外部工具、AI、报表脚本读取中台数据库。这里生成的 Key 只显示一次。</p>
        </div>
      </header>

      <section className="api-key-page-card">
        <div className="api-key-head">
          <div>
            <h3>Access Tokens</h3>
            <p>请求时使用 `Authorization: Bearer deca_...`，只读访问中台 Data API。</p>
          </div>
          <form className="api-key-form" onSubmit={submit}>
            <input className="text-input" value={name} onChange={event => setName(event.target.value)} type="text" placeholder="Key 名称，例如 AI Classifier" />
            <button className="btn primary" type="submit">生成 Key</button>
          </form>
        </div>

        {generatedKey ? (
          <div className="generated-api-key">
            <div className="generated-api-key-label">新 Key 只显示一次，请现在复制。</div>
            <code>{generatedKey}</code>
            <button className="btn ghost" type="button" onClick={() => onCopy(generatedKey)}>复制</button>
          </div>
        ) : null}

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

      <section className="api-key-page-card api-key-doc-card">
        <div>
          <h3>Data API Example</h3>
          <p>推荐入口：`GET /api/data/query`。这个接口只读你自己的数据库，不会调用 ReelFarm。</p>
        </div>
        <pre>{example}</pre>
        <button className="btn ghost" type="button" onClick={() => onCopy(example)}>复制示例</button>
      </section>
    </section>
  );
}
