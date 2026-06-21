'use client';

import { useMemo } from 'react';
import { formatFeishuMetric } from '@/lib/feishuReportHelpers';
import type {
  DailyFeishuAnalysisPayload,
  DailyFeishuProductSummary,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  DailyFeishuTotals,
  FeishuCardData,
  FeishuSendMode
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
  sendMode: FeishuSendMode;
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
  sendMode,
  analysisLoading,
  loading,
  analysisPayload,
  analysisError,
  selectedModel,
  generateAnalysis
}: FeishuAiPanelProps) {
  const includeAiDisabled = sendMode === 'card' || sendMode === 'template';
  const includeAiLabel = sendMode === 'card'
    ? '卡片模式暂不附带 AI 分析'
    : sendMode === 'template'
      ? '模板卡片暂不附带 AI 分析'
      : '仅在卡片失败转文本时附带 AI 分析';

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
            disabled={includeAiDisabled}
            onChange={event => setIncludeAi(event.target.checked)}
          />
          <span>{includeAiLabel}</span>
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
  totals: DailyFeishuTotals;
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
  products,
  sendMode
}: {
  payload: DailyFeishuPreviewPayload | null;
  loading: boolean;
  reportDate: string;
  products: DailyFeishuProductSummary[];
  sendMode: FeishuSendMode;
}) {
  const showCardPreview = Boolean(payload?.card_data);
  return (
    <>
      {showCardPreview ? <FeishuNativeCardPreview data={payload?.card_data || null} loading={loading} /> : null}
      <div className="feishu-report-layout">
        <section className="feishu-message-card">
          <div className="feishu-card-head">
            <div>
              <h2>文本兜底预览</h2>
              <p>
                业务日 {payload?.report?.report_date || reportDate} · 内容窗口{' '}
                {payload?.report?.business_window_local?.start || '—'} → {payload?.report?.business_window_local?.end || '—'}
              </p>
            </div>
          </div>
          <pre className="feishu-message-preview">{payload?.message || (loading ? '正在生成...' : '暂无预览')}</pre>
          {sendMode === 'template' && payload?.template_preview ? (
            <details className="feishu-template-preview">
              <summary>模板变量预览</summary>
              <pre>{JSON.stringify(payload.template_preview, null, 2)}</pre>
            </details>
          ) : null}
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
    </>
  );
}

function cardMetric(value: unknown) {
  return formatFeishuMetric(value);
}

function cardRate(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${formatFeishuMetric(value)}%`;
  return `${numeric.toFixed(2)}%`;
}

function postCoverage(product: { rfPublished?: number; rfExpected?: number }) {
  return `${cardMetric(product.rfPublished)}/${cardMetric(product.rfExpected)}`;
}

function compactAxisMetric(value: number) {
  if (!Number.isFinite(value)) return '0';
  const abs = Math.abs(value);
  if (abs >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (abs >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(Math.round(value));
}

function paddedRange(values: number[]) {
  const finite = values.filter(value => Number.isFinite(value));
  if (!finite.length) return { min: 0, max: 1 };
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) {
    const pad = Math.max(1, Math.abs(max) * 0.1);
    return { min: Math.max(0, min - pad), max: max + pad };
  }
  const pad = (max - min) * 0.12;
  return { min: Math.max(0, min - pad), max: max + pad };
}

function OverviewNativePreview({ data }: { data: FeishuCardData }) {
  const products = data.products || [];

  return (
    <div className="feishu-native-body">
      <div className="feishu-native-section-title">各 App 当日数据 · {data.bizDate || '—'}</div>
      <div className="feishu-native-table-scroll">
        <div className="feishu-native-daily-table">
          <div className="feishu-native-daily-row is-head">
            <span>App</span>
            <span>Post</span>
            <span>View</span>
            <span>RF Avg View</span>
            <span>Download</span>
            <span>下载/播放</span>
          </div>
          {products.length ? products.map(product => (
            <div className="feishu-native-daily-row" key={product.code || product.name}>
              <strong>{product.name || product.code || 'Product'}</strong>
              <span>{postCoverage(product)}</span>
              <span>{cardMetric(product.totalPlays)}</span>
              <span>{cardMetric(product.rfAvg)}</span>
              <span>{product.onboarding === null ? '—' : cardMetric(product.onboarding)}</span>
              <span>{cardRate(product.downloadRate)}</span>
            </div>
          )) : (
            <div className="feishu-native-daily-row">
              <strong>暂无产品</strong>
              <span>—</span>
              <span>—</span>
              <span>—</span>
              <span>—</span>
              <span>—</span>
            </div>
          )}
        </div>
      </div>
      <FeishuTrendChart trend={data.trend || []} />
    </div>
  );
}

function FeishuTrendChart({
  trend
}: {
  trend: NonNullable<FeishuCardData['trend']>;
}) {
  const chart = useMemo(() => {
    const rows = trend.map(row => ({
      label: row.label || row.date || '',
      view: Number(row.view || 0),
      download: Number(row.download || 0)
    }));
    const width = 760;
    const height = 310;
    const pad = { top: 24, right: 66, bottom: 44, left: 66 };
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const viewRange = paddedRange(rows.map(row => row.view));
    const downloadRange = paddedRange(rows.map(row => row.download));
    const xFor = (index: number) => pad.left + (rows.length <= 1 ? plotWidth / 2 : (plotWidth / (rows.length - 1)) * index);
    const yFor = (value: number, range: { min: number; max: number }) => {
      const ratio = (value - range.min) / Math.max(1, range.max - range.min);
      return pad.top + plotHeight - ratio * plotHeight;
    };
    const viewPoints = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.view, viewRange), value: row.view }));
    const downloadPoints = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.download, downloadRange), value: row.download }));
    const pathFor = (points: Array<{ x: number; y: number }>) =>
      points.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
    const grid = Array.from({ length: 5 }, (_, index) => {
      const ratio = index / 4;
      return {
        y: pad.top + ratio * plotHeight,
        view: viewRange.max - ratio * (viewRange.max - viewRange.min),
        download: downloadRange.max - ratio * (downloadRange.max - downloadRange.min),
      };
    });
    return {
      rows,
      width,
      height,
      pad,
      plotHeight,
      viewPoints,
      downloadPoints,
      viewPath: pathFor(viewPoints),
      downloadPath: pathFor(downloadPoints),
      grid,
    };
  }, [trend]);

  if (!chart.rows.length) {
    return (
      <div className="feishu-native-trend">
        <div className="feishu-native-section-title">View / Download 趋势</div>
        <p>暂无趋势数据。</p>
      </div>
    );
  }

  return (
    <div className="feishu-native-trend">
      <div className="feishu-native-section-title">View / Download 趋势</div>
      <div className="feishu-native-legend">
        <span className="is-view">View（左轴）</span>
        <span className="is-download">Download（右轴）</span>
      </div>
      <div className="feishu-native-chart-wrap">
        <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="View and Download trend">
          {chart.grid.map(line => (
            <g key={`grid-${line.y}`}>
              <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={line.y} y2={line.y} />
              <text x={chart.pad.left - 10} y={line.y + 4} textAnchor="end">{compactAxisMetric(line.view)}</text>
              <text x={chart.width - chart.pad.right + 10} y={line.y + 4} textAnchor="start">{compactAxisMetric(line.download)}</text>
            </g>
          ))}
          <path className="is-view-line" d={chart.viewPath} />
          <path className="is-download-line" d={chart.downloadPath} />
          {chart.viewPoints.map((point, index) => (
            <circle className="is-view-point" cx={point.x} cy={point.y} r="4.5" key={`view-${chart.rows[index].label}`} />
          ))}
          {chart.downloadPoints.map((point, index) => (
            <circle className="is-download-point" cx={point.x} cy={point.y} r="4.5" key={`download-${chart.rows[index].label}`} />
          ))}
          {chart.rows.map((row, index) => (
            <text className="is-x-label" x={chart.viewPoints[index].x} y={chart.height - 14} textAnchor="middle" key={`label-${row.label}`}>
              {row.label}
            </text>
          ))}
          <text className="is-axis-title" x="18" y={chart.pad.top + chart.plotHeight / 2} transform={`rotate(-90 18 ${chart.pad.top + chart.plotHeight / 2})`} textAnchor="middle">View</text>
          <text className="is-axis-title" x={chart.width - 18} y={chart.pad.top + chart.plotHeight / 2} transform={`rotate(90 ${chart.width - 18} ${chart.pad.top + chart.plotHeight / 2})`} textAnchor="middle">Download</text>
        </svg>
      </div>
    </div>
  );
}

function FeishuNativeCardPreview({ data, loading }: { data: FeishuCardData | null; loading: boolean }) {
  if (!data) {
    return (
      <section className="feishu-native-preview">
        <div className="feishu-native-empty">{loading ? '正在生成飞书卡片预览...' : '暂无飞书卡片预览'}</div>
      </section>
    );
  }

  return (
    <section className="feishu-native-preview">
      <div className="feishu-native-header">
        <div>
          <h2>Deca Growth 每日业务数据</h2>
          <p>业务日 {data.bizDate || '—'} · 内容窗口 {data.window || '—'}</p>
        </div>
        <span>Webhook 卡片</span>
      </div>
      <OverviewNativePreview data={data} />
    </section>
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
      {sendResult?.ok ? (
        <div className="feishu-success">
          已发送到飞书：{sendResult.sent_at || '刚刚'}
          {sendResult.mode ? ` · ${
            sendResult.mode === 'template'
              ? '模板卡片模式'
              : sendResult.mode === 'card'
                ? 'Webhook 卡片模式'
                : sendResult.fallback_reason
                  ? 'Webhook 卡片失败转文本'
                  : 'Webhook 卡片优先模式'
          }` : ''}
        </div>
      ) : null}
    </>
  );
}
