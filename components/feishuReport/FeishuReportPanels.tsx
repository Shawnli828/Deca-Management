'use client';

import { useMemo } from 'react';
import { formatFeishuMetric } from '@/lib/feishuReportHelpers';
import type {
  DailyFeishuProductSummary,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  FeishuCardData,
  FeishuSendMode
} from '@/lib/types';

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
  const overviewTrend = overviewTrendGroup(data);

  return (
    <div className="feishu-native-dashboard">
      <section className="feishu-native-overview-panel">
        <div className="feishu-native-panel-head">
          <div>
            <div className="feishu-native-section-title">总览 · 甲方产品</div>
            <p>业务日 {data.bizDate || '—'}</p>
          </div>
        </div>
        <FeishuOverviewKpis global={data.global || {}} />
        <FeishuTrendPanel groups={[overviewTrend]} />
      </section>
      <FeishuProductPreviewPanel products={data.products || []} />
    </div>
  );
}

function overviewTrendGroup(data: FeishuCardData) {
  const groups = data.trendGroups || [];
  return (
    groups.find(group => String(group.key || '').toLowerCase() === 'overview')
    || groups.find(group => String(group.label || '') === '总览')
    || { key: 'overview', label: '总览', trend: data.trend || [] }
  );
}

function FeishuOverviewKpis({
  global
}: {
  global: NonNullable<FeishuCardData['global']>;
}) {
  const items = [
    ['总播放', cardMetric(global.totalPlays), 'is-primary'],
    ['ReelFarm', cardMetric(global.rfPlays), ''],
    ['Clone', cardMetric(global.clonePlays), ''],
    ['Onboarding Unique', global.onboarding === null ? '—' : cardMetric(global.onboarding), 'is-green'],
    ['下载/播放', cardRate(global.downloadRate), 'is-amber']
  ];

  return (
    <div className="feishu-native-kpi-grid">
      {items.map(([label, value, tone]) => (
        <article className={tone ? String(tone) : undefined} key={String(label)}>
          <span>{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </div>
  );
}

function FeishuProductPreviewPanel({
  products
}: {
  products: NonNullable<FeishuCardData['products']>;
}) {
  return (
    <aside className="feishu-native-product-panel">
      <div className="feishu-native-panel-head">
        <div>
          <div className="feishu-native-section-title">产品视图</div>
          <p>单产品数据区</p>
        </div>
      </div>
      <div className="feishu-native-product-list">
        {products.length ? products.map(product => (
          <article key={product.code || product.name}>
            <div>
              <strong>{product.name || product.code || 'Product'}</strong>
              <span>{postCoverage(product)}</span>
            </div>
            <small>
              View {cardMetric(product.totalPlays)} · RF Avg {cardMetric(product.rfAvg)} · Download {product.onboarding === null ? '—' : cardMetric(product.onboarding)}
            </small>
          </article>
        )) : (
          <p className="feishu-native-empty">暂无产品数据。</p>
        )}
      </div>
    </aside>
  );
}

function FeishuTrendPanel({
  groups
}: {
  groups: NonNullable<FeishuCardData['trendGroups']>;
}) {
  const visibleGroups = groups.slice(0, 4);

  return (
    <div className="feishu-native-trend">
      <div className="feishu-native-trend-head">
        <div className="feishu-native-section-title">View / Download 趋势</div>
        <div className="feishu-native-legend">
          <span className="is-view">View</span>
          <span className="is-download">Download</span>
        </div>
      </div>
      {visibleGroups.length ? (
        <div className={`feishu-native-trend-grid${visibleGroups.length === 1 ? ' is-single' : ''}`}>
          {visibleGroups.map(group => (
            <FeishuMiniTrendChart
              key={group.key || group.label}
              title={(group.label || group.key) === '总览' ? '全部汇总' : (group.label || group.key || '趋势')}
              trend={group.trend || []}
            />
          ))}
        </div>
      ) : (
        <p>暂无趋势数据。</p>
      )}
    </div>
  );
}

function FeishuMiniTrendChart({
  title,
  trend
}: {
  title: string;
  trend: NonNullable<FeishuCardData['trend']>;
}) {
  const chart = useMemo(() => {
    const rows = trend.map(row => ({
      label: row.label || row.date || '',
      view: Number(row.view || 0),
      download: Number(row.download || 0)
    }));
    const width = 320;
    const height = 170;
    const pad = { top: 12, right: 36, bottom: 26, left: 42 };
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
    const pathFor = (points: Array<{ x: number; y: number }>) => {
      if (!points.length) return '';
      if (points.length === 1) return `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
      return points.slice(1).reduce((path, point, index) => {
        const previous = points[index];
        const midX = (previous.x + point.x) / 2;
        return `${path} C${midX.toFixed(1)} ${previous.y.toFixed(1)} ${midX.toFixed(1)} ${point.y.toFixed(1)} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
      }, `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`);
    };
    const grid = Array.from({ length: 4 }, (_, index) => {
      const ratio = index / 3;
      return {
        y: pad.top + ratio * plotHeight,
        view: viewRange.max - ratio * (viewRange.max - viewRange.min),
        download: downloadRange.max - ratio * (downloadRange.max - downloadRange.min),
      };
    });
    const labelIndexes = rows.length <= 5
      ? rows.map((_, index) => index)
      : Array.from(new Set([0, 2, 4, rows.length - 1])).filter(index => index < rows.length);
    return {
      rows,
      width,
      height,
      pad,
      viewPoints,
      downloadPoints,
      viewPath: pathFor(viewPoints),
      downloadPath: pathFor(downloadPoints),
      grid,
      labelIndexes,
    };
  }, [trend]);

  if (!chart.rows.length) {
    return (
      <div className="feishu-native-mini-chart is-empty">
        <div className="feishu-native-mini-chart-head">
          <strong>{title}</strong>
        </div>
        <p>暂无趋势数据。</p>
      </div>
    );
  }

  return (
    <div className="feishu-native-mini-chart">
      <div className="feishu-native-mini-chart-head">
        <strong>{title}</strong>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        role="img"
        aria-label={`${title} View and Download trend`}
      >
          {chart.grid.map(line => (
            <g key={`grid-${line.y}`}>
              <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={line.y} y2={line.y} />
              <text className="is-y-label" x={chart.pad.left - 8} y={line.y + 3} textAnchor="end">
                {compactAxisMetric(line.view)}
              </text>
              <text className="is-y-label" x={chart.width - chart.pad.right + 8} y={line.y + 3} textAnchor="start">
                {compactAxisMetric(line.download)}
              </text>
            </g>
          ))}
          <path className="is-view-line" d={chart.viewPath} />
          <path className="is-download-line" d={chart.downloadPath} />
          {chart.viewPoints.map((point, index) => (
            <circle className="is-view-point" cx={point.x} cy={point.y} r="2.2" key={`view-${index}-${chart.rows[index].label}`} />
          ))}
          {chart.downloadPoints.map((point, index) => (
            <circle className="is-download-point" cx={point.x} cy={point.y} r="2.2" key={`download-${index}-${chart.rows[index].label}`} />
          ))}
          {chart.labelIndexes.map(index => (
            <text
              className="is-x-label"
              x={chart.viewPoints[index].x}
              y={chart.height - 6}
              textAnchor={index === 0 ? 'start' : 'end'}
              key={`label-${index}-${chart.rows[index].label}`}
            >
              {chart.rows[index].label}
            </text>
          ))}
        </svg>
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
