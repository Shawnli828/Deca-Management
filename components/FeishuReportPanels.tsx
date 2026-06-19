'use client';

import { formatFeishuMetric } from '@/lib/feishuReportHelpers';
import type {
  DailyFeishuAnalysisPayload,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult
} from '@/lib/types';

type FeishuAiPanelProps = {
  model: string;
  setModel: (value: string) => void;
  modelOptions: string[];
  modelListStatus: string;
  customModel: string;
  setCustomModel: (value: string) => void;
  includeAi: boolean;
  setIncludeAi: (value: boolean) => void;
  analysisLoading: boolean;
  loading: boolean;
  analysisPayload: DailyFeishuAnalysisPayload | null;
  analysisError: string;
  selectedModel: string;
  generateAnalysis: () => void;
};

export function FeishuAiPanel({
  model,
  setModel,
  modelOptions,
  modelListStatus,
  customModel,
  setCustomModel,
  includeAi,
  setIncludeAi,
  analysisLoading,
  loading,
  analysisPayload,
  analysisError,
  selectedModel,
  generateAnalysis
}: FeishuAiPanelProps) {
  return (
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
  );
}

export function FeishuReportSummary({
  totals,
  downloadRate
}: {
  totals: Record<string, any>;
  downloadRate: number | null;
}) {
  const summaryItems = [
    ['总播放', totals.total_views],
    ['ReelFarm', totals.reelfarm_views],
    ['Clone', totals.clone_views],
    ['Onboarding Unique', totals.downloads],
    ['下载/播放', downloadRate === null ? null : `${downloadRate.toFixed(2)}%`]
  ];

  return (
    <section className="feishu-report-summary">
      {summaryItems.map(([label, value]) => (
        <article key={label as string}>
          <span>{label}</span>
          <strong>{typeof value === 'string' ? value : formatFeishuMetric(value)}</strong>
        </article>
      ))}
    </section>
  );
}

export function FeishuReportLayout({
  payload,
  loading,
  reportDate,
  products
}: {
  payload: DailyFeishuPreviewPayload | null;
  loading: boolean;
  reportDate: string;
  products: Array<Record<string, any>>;
}) {
  return (
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
              <small>播放 {formatFeishuMetric(product.total_views)} · Onboarding {formatFeishuMetric(product.downloads)}</small>
            </article>
          )) : (
            <p className="feishu-empty">暂无产品数据。</p>
          )}
        </div>
      </aside>
    </div>
  );
}

export function FeishuStatusMessages({
  error,
  sendResult
}: {
  error: string;
  sendResult: DailyFeishuSendResult | null;
}) {
  return (
    <>
      {error ? <div className="growth-error">{error}</div> : null}
      {sendResult?.ok ? <div className="feishu-success">已发送到飞书：{sendResult.sent_at || '刚刚'}</div> : null}
    </>
  );
}
