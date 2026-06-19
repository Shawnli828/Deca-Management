'use client';

const baseUrl = 'https://deca-management.vercel.app';

const authCurl = `curl -X GET ${baseUrl}/api/data/query?resource=summary \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`;

const accountsCurl = `curl "${baseUrl}/api/data/query?resource=accounts&product_code=DB&country_code=GE&days=7" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`;

const postsCurl = `curl "${baseUrl}/api/data/query?resource=posts&product_code=DB&country_code=GE&date_from=2026-04-30&limit=50" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`;

const resourceCatalog = [
  ['summary', '中台总览数据'],
  ['countries', '产品 × 国家汇总'],
  ['accounts', '账号摘要列表'],
  ['account_posts', '单账号分页 posts'],
  ['posts', '详细 post rows'],
  ['materials', '素材/video rows'],
  ['daily_metrics', '每日快照趋势'],
  ['top_posts', '高表现内容'],
  ['country_cards', '兼容旧卡片结构']
];

export function DataApiReference({ onCopy }: { onCopy: (value: string) => void }) {
  return (
    <section className="api-reference">
      <nav className="api-reference-nav" aria-label="API sections">
        <a href="#api-overview">Overview</a>
        <a href="#api-auth">Authentication</a>
        <a href="#api-summary">Summary</a>
        <a href="#api-accounts">Accounts</a>
        <a href="#api-posts">Posts</a>
        <a href="#api-trends">Daily Metrics</a>
        <a href="#api-errors">Errors</a>
      </nav>

      <section className="api-reference-hero" id="api-overview">
        <div>
          <p className="api-reference-kicker">API Reference</p>
          <h3>Deca Growth Data API</h3>
          <p>给外部 AI、脚本和报表工具读取中台数据库。普通 dashboard 渲染和外部工具都可以使用同一个只读查询入口。</p>
          <div className="api-reference-pills" aria-label="API traits">
            <span>Read-only</span>
            <span>Bearer API Key</span>
            <span>JSON Response</span>
            <span>No ReelFarm fetch</span>
          </div>
        </div>
        <div className="api-base-card">
          <span>Base URL</span>
          <code>{baseUrl}</code>
          <small>所有 `/api/data/query` 请求只读本地数据库，不会调用 ReelFarm。</small>
        </div>
      </section>

      <section className="api-resource-catalog" aria-label="Supported resources">
        {resourceCatalog.map(([resource, description]) => (
          <div className="api-resource-card" key={resource}>
            <code>{resource}</code>
            <span>{description}</span>
          </div>
        ))}
      </section>

      <section className="api-reference-section" id="api-auth">
        <div className="api-reference-copy">
          <h3>Authentication</h3>
          <p>外部请求必须带 dashboard 生成的 API Key。Key 只显示一次，可以在 API Keys 面板停用。</p>
          <div className="api-param-list">
            <div><strong>Header</strong><span>Authorization</span></div>
            <div><strong>Value</strong><span>Bearer YOUR_DECA_API_KEY</span></div>
            <div><strong>Key Prefix</strong><span>deca_...</span></div>
          </div>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{authCurl}</pre>
          <button className="btn ghost" type="button" onClick={() => onCopy(authCurl)}>复制</button>
        </div>
      </section>

      <section className="api-reference-section" id="api-summary">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Summary</h3>
          <code className="api-endpoint">/api/data/query?resource=summary</code>
          <p>返回产品、国家、账号、素材、posts 和总互动指标。适合健康检查和报表顶部数字。</p>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Response · 200</div>
          <pre>{`{
  "ok": true,
  "resource": "summary",
  "data": {
    "products": 3,
    "accounts": 234,
    "posts": 8026,
    "total_views": 123456
  }
}`}</pre>
        </div>
      </section>

      <section className="api-reference-section" id="api-accounts">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Accounts</h3>
          <code className="api-endpoint">/api/data/query?resource=accounts</code>
          <p>快速读取某个产品和国家下的账号摘要，不返回每个 post 或图片，适合列表页。</p>
          <div className="api-param-list">
            <div><strong>product_code</strong><span>DB / DL / DM</span></div>
            <div><strong>country_code</strong><span>GE / US / FR</span></div>
            <div><strong>days</strong><span>7 / 14 / 30</span></div>
          </div>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{accountsCurl}</pre>
          <button className="btn ghost" type="button" onClick={() => onCopy(accountsCurl)}>复制</button>
        </div>
      </section>

      <section className="api-reference-section" id="api-posts">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Posts</h3>
          <code className="api-endpoint">/api/data/query?resource=posts</code>
          <p>详细 post rows，包含产品、国家、账号、automation、hook、prompt、slides、发布时间和 metrics。最适合 AI 做 concept / format 分类。</p>
          <div className="api-param-list">
            <div><strong>date_from</strong><span>2026-04-30</span></div>
            <div><strong>limit</strong><span>默认 50，最大 500</span></div>
            <div><strong>offset</strong><span>分页偏移</span></div>
          </div>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{postsCurl}</pre>
          <button className="btn ghost" type="button" onClick={() => onCopy(postsCurl)}>复制</button>
        </div>
      </section>

      <section className="api-reference-section">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Account Posts</h3>
          <code className="api-endpoint">/api/data/query?resource=account_posts</code>
          <p>只读取一个账号的 posts/materials，支持 limit/offset。Dashboard 展开账号时使用这种渐进加载方式。</p>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{`curl "${baseUrl}/api/data/query?resource=account_posts&product_code=DB&country_code=GE&account_id=user123&limit=4&offset=0" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`}</pre>
        </div>
      </section>

      <section className="api-reference-section">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Materials</h3>
          <code className="api-endpoint">/api/data/query?resource=materials</code>
          <p>以素材/video 为中心读取 hook、prompt、slideshow_images 和关联 post。适合素材库或 AI 只看素材内容。</p>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{`curl "${baseUrl}/api/data/query?resource=materials&product_code=DB&country_code=GE&limit=50" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`}</pre>
        </div>
      </section>

      <section className="api-reference-section" id="api-trends">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Daily Metrics</h3>
          <code className="api-endpoint">/api/data/query?resource=daily_metrics</code>
          <p>读取每日快照和 delta，用于观察素材数据变化，而不是只看最新总数。</p>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{`curl "${baseUrl}/api/data/query?resource=daily_metrics&product_code=DB&country_code=GE&days=7" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`}</pre>
        </div>
      </section>

      <section className="api-reference-section">
        <div className="api-reference-copy">
          <span className="api-method get">GET</span>
          <h3>Top Posts</h3>
          <code className="api-endpoint">/api/data/query?resource=top_posts</code>
          <p>按指标排序取高表现内容。metric 支持 view_count、like_count、comment_count、share_count、bookmark_count。</p>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Example Request</div>
          <pre>{`curl "${baseUrl}/api/data/query?resource=top_posts&product_code=DB&country_code=GE&metric=view_count&limit=20" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`}</pre>
        </div>
      </section>

      <section className="api-reference-section" id="api-errors">
        <div className="api-reference-copy">
          <h3>Error Codes</h3>
          <p>所有错误都返回 JSON。没有 key 或 key 被停用会返回 401。</p>
          <div className="api-param-list">
            <div><strong>401</strong><span>Unauthorized</span></div>
            <div><strong>400</strong><span>Unsupported resource or metric</span></div>
            <div><strong>500</strong><span>Server/database error</span></div>
          </div>
        </div>
        <div className="api-code-card">
          <div className="api-code-head">Error Response</div>
          <pre>{`{
  "ok": false,
  "error": "Unauthorized"
}`}</pre>
        </div>
      </section>

      <section className="api-reference-footer">
        <div>
          <h3>完整文件</h3>
          <p>本地文档：<code>AI_API_DOC.md</code>。线上 OpenAPI：<code>/api/docs</code> 和 <code>/api/openapi.json</code>。</p>
        </div>
      </section>
    </section>
  );
}
