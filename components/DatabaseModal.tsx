'use client';

import type { DatabaseSnapshot, ExternalApiKey } from '@/lib/types';
import { FormEvent, useState } from 'react';

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
  const [name, setName] = useState('');
  const [tab, setTab] = useState<'keys' | 'docs'>('keys');
  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onCreateKey(name || 'API Key');
    setName('');
  }

  return (
    <div className="database-modal is-open" onClick={event => {
      if (event.target === event.currentTarget) onClose();
    }}>
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
          {tab === 'keys' ? <section className="api-key-panel">
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
          </section> : (
            <section className="api-doc-panel">
              <div className="api-doc-block">
                <h3>Base URL</h3>
                <code>https://deca-management.vercel.app</code>
              </div>
              <div className="api-doc-block">
                <h3>Authentication</h3>
                <p>所有外部工具请求都需要在 header 加 Bearer Token。</p>
                <pre>{`Authorization: Bearer YOUR_DECA_API_KEY`}</pre>
              </div>
              <div className="api-doc-block">
                <h3>推荐入口</h3>
                <pre>{`GET /api/data/query?resource=summary`}</pre>
                <p>这个接口只读本地数据库，不会调用 ReelFarm。</p>
              </div>
              <div className="api-doc-grid">
                <div>
                  <h4>summary</h4>
                  <p>总览 products / accounts / posts / metrics。</p>
                </div>
                <div>
                  <h4>countries</h4>
                  <p>产品和国家/地区的汇总数据。</p>
                </div>
                <div>
                  <h4>accounts</h4>
                  <p>某产品国家下的账号摘要，不含图片明细。</p>
                </div>
                <div>
                  <h4>account_posts</h4>
                  <p>单个账号的分页素材和 post 明细。</p>
                </div>
                <div>
                  <h4>posts</h4>
                  <p>最适合 AI 分类的详细 post rows。</p>
                </div>
                <div>
                  <h4>materials</h4>
                  <p>按素材/video 读取 hook、prompt、slides。</p>
                </div>
                <div>
                  <h4>daily_metrics</h4>
                  <p>读取每日快照和趋势变化。</p>
                </div>
                <div>
                  <h4>top_posts</h4>
                  <p>按 views / likes 等指标找高表现素材。</p>
                </div>
              </div>
              <div className="api-doc-block">
                <h3>常用测试</h3>
                <pre>{`curl "https://deca-management.vercel.app/api/data/query?resource=summary" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`}</pre>
                <button className="btn ghost" type="button" onClick={() => onCopy(`curl "https://deca-management.vercel.app/api/data/query?resource=summary" \\\n  -H "Authorization: Bearer YOUR_DECA_API_KEY"`)}>复制</button>
              </div>
              <div className="api-doc-block">
                <h3>读取 DB + GE posts</h3>
                <pre>{`curl "https://deca-management.vercel.app/api/data/query?resource=posts&product_code=DB&country_code=GE&limit=50" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`}</pre>
                <button className="btn ghost" type="button" onClick={() => onCopy(`curl "https://deca-management.vercel.app/api/data/query?resource=posts&product_code=DB&country_code=GE&limit=50" \\\n  -H "Authorization: Bearer YOUR_DECA_API_KEY"`)}>复制</button>
              </div>
              <div className="api-doc-block">
                <h3>完整文档</h3>
                <p>本地文件：<code>AI_API_DOC.md</code>。线上 OpenAPI：<code>/api/docs</code> 和 <code>/api/openapi.json</code>。</p>
              </div>
            </section>
          )}
        </div>
      </section>
    </div>
  );
}
