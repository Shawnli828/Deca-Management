'use client';

import { useMemo, useState } from 'react';
import { formatFeishuMetric } from '@/lib/feishuReportHelpers';
import type {
  DailyFeishuAnalysisPayload,
  DailyFeishuProductSummary,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  DailyFeishuTotals,
  FeishuCardData,
  FeishuCardMetricProduct,
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
  const includeAiDisabled = sendMode === 'card';
  const includeAiLabel = sendMode === 'text'
    ? '发送文本时附带 AI 分析'
    : sendMode === 'card'
      ? '卡片模式暂不附带 AI 分析'
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
  const showCardPreview = sendMode !== 'text' && Boolean(payload?.card_data);
  return (
    <>
      {showCardPreview ? <FeishuNativeCardPreview data={payload?.card_data || null} loading={loading} /> : null}
      <div className="feishu-report-layout">
        <section className="feishu-message-card">
          <div className="feishu-card-head">
            <div>
              <h2>{sendMode === 'text' ? '飞书文本预览' : '文本兜底预览'}</h2>
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
    </>
  );
}

function cardMetric(value: unknown) {
  return formatFeishuMetric(value);
}

function cardRate(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return `${formatFeishuMetric(value)}%`;
}

function nativeBar(value: unknown, max: number, width = 14) {
  const numeric = Number(value || 0);
  if (!max || !Number.isFinite(numeric)) return '░'.repeat(width);
  const filled = Math.max(0, Math.min(width, Math.round((numeric / max) * width)));
  return '█'.repeat(filled) + '░'.repeat(width - filled);
}

function FeishuKpiRows({ rows }: { rows: Array<Array<[string, unknown]>> }) {
  return (
    <div className="feishu-native-kpis">
      {rows.map((row, index) => (
        <div className="feishu-native-kpi-row" key={index}>
          {row.map(([label, value], itemIndex) => (
            <div className="feishu-native-kpi" key={`${label}-${itemIndex}`}>
              {label ? (
                <>
                  <span>{label}</span>
                  <strong>{String(value)}</strong>
                </>
              ) : null}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function OverviewNativePreview({ data }: { data: FeishuCardData }) {
  const global = data.global || {};
  const products = data.products || [];
  const playMax = Math.max(...products.map(product => Number(product.totalPlays || 0)), 0);
  const avgMax = Math.max(...products.map(product => Number(product.rfAvg || 0)), 0);
  const sortedByAvg = [...products].sort((a, b) => Number(b.rfAvg || 0) - Number(a.rfAvg || 0));
  const totalUnsent = products.reduce((sum, product) => sum + Number(product.unsent || 0), 0);
  const totalZero = products.reduce((sum, product) => sum + Number(product.zeroPlay || 0), 0);

  return (
    <div className="feishu-native-body">
      <FeishuKpiRows rows={[
        [['总播放', cardMetric(global.totalPlays)], ['RF 总播放', cardMetric(global.rfPlays)], ['Clone 总播放', cardMetric(global.clonePlays)]],
        [['RF 发布', `${cardMetric(global.rfPublished)}/${cardMetric(global.rfExpected)}`], ['RF 均播', cardMetric(global.rfAvg)], ['Clone 均播', cardMetric(global.cloneAvg)]],
        [['Onboarding', cardMetric(global.onboarding)], ['下载/播放', cardRate(global.downloadRate)], ['', '']]
      ]} />
      <div className="feishu-native-alert">未发送 {totalUnsent} · 0播警告 {totalZero}</div>
      <FeishuBarBlock title="产品线总播放量" products={products} max={playMax} valueKey="totalPlays" />
      <FeishuBarBlock title="产品线 RF 均播" products={sortedByAvg} max={avgMax} valueKey="rfAvg" />
      <div className="feishu-native-table">
        <strong>Onboarding 与下载/播放</strong>
        {products.map(product => (
          <div key={`${product.name}-onboarding`}>
            <span>{product.name}</span>
            <span>{product.onboarding === null ? '未配置' : cardMetric(product.onboarding)}</span>
            <span>{cardRate(product.downloadRate)}</span>
          </div>
        ))}
      </div>
      <div className="feishu-native-table">
        <strong>异常账号分布</strong>
        {products.map(product => (
          <div key={`${product.name}-anomaly`}>
            <span>{product.name}</span>
            <span className={product.unsent ? 'is-danger' : ''}>{product.unsent || 0} 未发送</span>
            <span className={product.zeroPlay ? 'is-danger' : ''}>{product.zeroPlay || 0} 0播</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FeishuBarBlock({
  title,
  products,
  max,
  valueKey
}: {
  title: string;
  products: FeishuCardMetricProduct[];
  max: number;
  valueKey: keyof FeishuCardMetricProduct;
}) {
  return (
    <div className="feishu-native-bars">
      <strong>{title}</strong>
      {products.map(product => (
        <div className="feishu-native-bar-line" key={`${title}-${product.name}`}>
          <code>{nativeBar(product[valueKey], max)}</code>
          <span>{product.name}</span>
          <b>{cardMetric(product[valueKey])}</b>
        </div>
      ))}
    </div>
  );
}

function ProductNativePreview({ product }: { product: FeishuCardMetricProduct }) {
  const onboarding = product.onboarding === null ? '未配置' : cardMetric(product.onboarding);
  return (
    <div className="feishu-native-body">
      <FeishuKpiRows rows={[
        [['总播放', cardMetric(product.totalPlays)], ['RF 总播放', cardMetric(product.rfPlays)], ['Clone 总播放', cardMetric(product.clonePlays)]],
        [['RF 发布', `${cardMetric(product.rfPublished)}/${cardMetric(product.rfExpected)}`], ['RF 均播', cardMetric(product.rfAvg)], ['Clone 均播', cardMetric(product.cloneAvg)]],
        [['Onboarding', onboarding], ['下载/播放', cardRate(product.downloadRate)], ['', '']],
        [['未发送', String(product.unsent || 0)], ['0播警告', String(product.zeroPlay || 0)], ['', '']]
      ]} />
      <div className="feishu-native-countries">
        <strong>国家 RF 均播</strong>
        {(product.countries || []).length ? product.countries?.map(country => (
          <div key={`${product.name}-${country.name}`}>
            <span>{country.flag} {country.name}</span>
            <b>{cardMetric(country.rfAvg)}</b>
            <small>{cardMetric(country.posts)} posts</small>
          </div>
        )) : <p>暂无 RF 发布数据</p>}
      </div>
      {(product.anomalyGroups || []).map(group => (
        <div className="feishu-native-anomaly" key={`${product.name}-${group.title}`}>
          <strong>{group.title}</strong>
          {(group.accounts || []).map(account => (
            <div key={`${account.handle}-${account.batch}`}>
              <span>{account.flag} {account.handle}</span>
              <small>{account.batch}</small>
            </div>
          ))}
          {group.more ? <em>{group.more}</em> : null}
        </div>
      ))}
    </div>
  );
}

function FeishuNativeCardPreview({ data, loading }: { data: FeishuCardData | null; loading: boolean }) {
  const [activeTab, setActiveTab] = useState('overview');
  const products = data?.products || [];
  const selectedProduct = useMemo(
    () => products.find(product => product.name === activeTab) || null,
    [activeTab, products]
  );

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
        <span>飞书兼容版</span>
      </div>
      <div className="feishu-native-tabs">
        <button type="button" className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>
          总览
        </button>
        {products.map(product => (
          <button
            type="button"
            className={activeTab === product.name ? 'active' : ''}
            key={product.name}
            onClick={() => setActiveTab(product.name || '')}
          >
            {product.name}
          </button>
        ))}
      </div>
      {selectedProduct ? <ProductNativePreview product={selectedProduct} /> : <OverviewNativePreview data={data} />}
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
          {sendResult.mode ? ` · ${sendResult.mode === 'card' ? '卡片模式' : sendResult.mode === 'text' ? '文本模式' : '卡片失败转文本'}` : ''}
        </div>
      ) : null}
    </>
  );
}
