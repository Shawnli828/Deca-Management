'use client';

import { localIsoDate, useFeishuReport } from '@/hooks/useFeishuReport';
import { formatNumber } from '@/lib/utils';

function metric(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return formatNumber(value);
}

export function FeishuReportPage() {
  const {
    reportDate,
    setReportDate,
    payload,
    loading,
    sending,
    error,
    sendResult,
    model,
    setModel,
    modelOptions,
    modelListStatus,
    customModel,
    setCustomModel,
    includeAi,
    setIncludeAi,
    analysisLoading,
    analysisPayload,
    analysisError,
    totals,
    products,
    downloadRate,
    selectedModel,
    loadPreview,
    sendReport,
    generateAnalysis
  } = useFeishuReport();

  return (
    <section className="feishu-report-page">
      <header className="feishu-report-hero">
        <div>
          <p className="dashboard-kicker">AI Feishu Report</p>
          <h1>Feishu Report</h1>
          <p>每日业务数据先在这里生成可检查文本；后续可以接入 LLM 洞察、图片渲染，再一起发送到飞书。</p>
        </div>
        <div className="feishu-report-actions">
          <label>
            <span>业务日</span>
            <input type="date" value={reportDate} max={localIsoDate()} onChange={event => setReportDate(event.target.value)} />
          </label>
          <button type="button" onClick={() => loadPreview(reportDate)} disabled={loading}>
            {loading ? '生成中...' : '生成预览'}
          </button>
          <button className="primary" type="button" onClick={sendReport} disabled={sending || loading}>
            {sending ? '发送中...' : '发送飞书'}
          </button>
        </div>
      </header>

      {error ? <div className="growth-error">{error}</div> : null}
      {sendResult?.ok ? <div className="feishu-success">已发送到飞书：{sendResult.sent_at || '刚刚'}</div> : null}

      <section className="feishu-flow-grid" aria-label="AI 日报流程">
        {[
          ['01', 'Data Snapshot', '读取 Daily Metric 当前业务日数据', 'Ready'],
          ['02', 'LLM Insight', '让模型总结波动、异常和重点产品', analysisPayload ? (analysisPayload.configured ? 'Ready' : 'Needs Key') : 'Optional'],
          ['03', 'Image Render', '后续把总结渲染成日报图片', 'Planned'],
          ['04', 'Feishu Send', includeAi ? '发送文本时附带 AI 分析' : '手动发送当前日报文本', 'Ready']
        ].map(([index, title, description, status]) => (
          <article className="feishu-flow-card" key={title}>
            <span>{index}</span>
            <strong>{title}</strong>
            <p>{description}</p>
            <small>{status}</small>
          </article>
        ))}
      </section>

      <section className="feishu-ai-panel">
        <div className="feishu-ai-copy">
          <p className="dashboard-kicker">LLM Insight</p>
          <h2>日报 AI 分析</h2>
          <p>
            模型会读取当前业务日和昨日数据，先找发布缺口、播放变化、Onboarding 和下载/播放转化，再生成可以直接放进飞书的中文分析。
          </p>
          <small>
            API Key 只在后端环境变量读取：<code>LLM_API_KEY</code> 或 <code>OPENAI_API_KEY</code>。
            可选配置：<code>LLM_MODEL</code>、<code>LLM_API_BASE</code>。
          </small>
        </div>
        <div className="feishu-ai-workspace">
          <div className="feishu-ai-controls">
            <label>
              <span>模型</span>
              <select value={model} onChange={event => setModel(event.target.value)}>
                {modelOptions.map(option => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <label>
              <span>自定义模型</span>
              <input
                value={customModel}
                onChange={event => setCustomModel(event.target.value)}
                placeholder="例如 gpt-4.1-mini"
              />
            </label>
            <button type="button" onClick={generateAnalysis} disabled={analysisLoading || loading}>
              {analysisLoading ? '分析中...' : '生成分析'}
            </button>
          </div>
          {modelListStatus ? <small className="feishu-ai-model-note">{modelListStatus}</small> : null}
          <label className="feishu-ai-checkbox">
            <input
              type="checkbox"
              checked={includeAi}
              onChange={event => setIncludeAi(event.target.checked)}
            />
            <span>发送飞书时附带 AI 分析</span>
          </label>
          {analysisError ? <div className="feishu-ai-error">{analysisError}</div> : null}
          <div className="feishu-ai-output">
            {analysisPayload ? (
              <>
                <div className="feishu-ai-output-meta">
                  <strong>{analysisPayload.needs_api_key ? '等待配置 API Key' : '分析结果'}</strong>
                  <span>{analysisPayload.model || selectedModel}</span>
                </div>
                <p>{analysisPayload.analysis}</p>
              </>
            ) : (
              <p>
                选择模型后点击“生成分析”。如果还没配置 API Key，这里会提示需要配置哪些环境变量。
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="feishu-report-summary">
        {[
          ['总播放', totals.total_views],
          ['ReelFarm', totals.reelfarm_views],
          ['Clone', totals.clone_views],
          ['Onboarding Unique', totals.downloads],
          ['下载/播放', downloadRate === null ? null : `${downloadRate.toFixed(2)}%`]
        ].map(([label, value]) => (
          <article key={label as string}>
            <span>{label}</span>
            <strong>{typeof value === 'string' ? value : metric(value)}</strong>
          </article>
        ))}
      </section>

      <div className="feishu-report-layout">
        <section className="feishu-message-card">
          <div className="feishu-card-head">
            <div>
              <h2>飞书消息预览</h2>
              <p>
                业务日 {payload?.report?.report_date || reportDate} · 内容窗口{' '}
                {payload?.report?.business_window_local?.start || '—'} → {payload?.report?.business_window_local?.end || '—'}
              </p>
            </div>
          </div>
          <pre className="feishu-message-preview">{payload?.message || (loading ? '正在生成...' : '暂无预览')}</pre>
        </section>

        <aside className="feishu-product-card">
          <div className="feishu-card-head">
            <div>
              <h2>产品拆分</h2>
              <p>用于检查发送前每个产品的数据是否合理。</p>
            </div>
          </div>
          <div className="feishu-product-list">
            {products.length ? products.map(product => (
              <article key={String(product.product_code || product.product_name)}>
                <div>
                  <strong>{String(product.product_name || product.product_code || 'Product')}</strong>
                  <span>{String(product.product_code || '')}</span>
                </div>
                <small>播放 {metric(product.total_views)} · Onboarding {metric(product.downloads)}</small>
              </article>
            )) : (
              <p className="feishu-empty">暂无产品数据。</p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
