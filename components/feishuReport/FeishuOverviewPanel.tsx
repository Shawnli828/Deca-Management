'use client';

import type { FeishuCardData } from '@/lib/types';
import { cardMetric, cardRate, postCoverage, productKey } from './FeishuReportShared';
import { FeishuTrendPanel } from './FeishuTrendCharts';

export function FeishuOverviewPanel({ data }: { data: FeishuCardData }) {
  const overviewTrend = overviewTrendGroup(data);

  return (
    <section className="feishu-native-overview-panel">
      <div className="feishu-native-panel-head">
        <div>
          <div className="feishu-native-section-title">总览 · 甲方产品</div>
          <p>业务日 {data.bizDate || '—'} · 内容窗口 {data.window || '—'}</p>
        </div>
        <span>Webhook 总览卡片</span>
      </div>
      <FeishuOverviewKpis global={data.global || {}} />
      <FeishuTrendPanel groups={[overviewTrend]} />
      <FeishuOverviewProductTable products={data.products || []} global={data.global || {}} />
    </section>
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
    ['RF Total View', cardMetric(global.rfPlays), ''],
    ['Clone Total View', cardMetric(global.clonePlays), ''],
    ['Onboarding Unique', global.onboarding === null ? '—' : cardMetric(global.onboarding), 'is-green'],
    ['转化', cardRate(global.downloadRate), 'is-amber'],
    ['Post', postCoverage(global), '']
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

function FeishuOverviewProductTable({
  products,
  global
}: {
  products: NonNullable<FeishuCardData['products']>;
  global: NonNullable<FeishuCardData['global']>;
}) {
  const rows = [
    ...products.map(product => ({
      key: productKey(product) || product.name || 'product',
      label: product.name || product.code || 'Product',
      ttlView: product.totalPlays,
      rfView: product.rfPlays,
      cloneView: product.clonePlays,
      download: product.onboarding,
      downloadRate: product.downloadRate,
      posted: postCoverage(product),
      isTotal: false,
    })),
    {
      key: 'total',
      label: '合计',
      ttlView: global.totalPlays,
      rfView: global.rfPlays,
      cloneView: global.clonePlays,
      download: global.onboarding,
      downloadRate: global.downloadRate,
      posted: postCoverage(global),
      isTotal: true,
    },
  ];

  return (
    <div className="feishu-overview-product-section">
      <div className="feishu-native-section-title">甲方产品明细</div>
      <div className="feishu-overview-product-scroll">
        <div className="feishu-overview-product-table" role="table" aria-label="甲方产品明细">
          <div className="feishu-overview-product-row is-head" role="row">
            <span role="columnheader">App</span>
            <span role="columnheader">TTL View</span>
            <span role="columnheader">RF View</span>
            <span role="columnheader">Clone View</span>
            <span role="columnheader">Download</span>
            <span role="columnheader">Download/TTL View</span>
            <span role="columnheader">Posted/Supposed</span>
          </div>
          {products.length ? rows.map(row => (
            <div className={`feishu-overview-product-row${row.isTotal ? ' is-total' : ''}`} role="row" key={row.key}>
              <strong role="cell">{row.label}</strong>
              <span role="cell">{cardMetric(row.ttlView)}</span>
              <span role="cell">{cardMetric(row.rfView)}</span>
              <span role="cell">{cardMetric(row.cloneView)}</span>
              <span role="cell">{row.download === null || row.download === undefined ? '—' : cardMetric(row.download)}</span>
              <span role="cell">{cardRate(row.downloadRate)}</span>
              <span role="cell">{row.posted}</span>
            </div>
          )) : (
            <div className="feishu-overview-product-row is-empty" role="row">
              <strong role="cell">暂无甲方产品数据。</strong>
              <span role="cell">—</span>
              <span role="cell">—</span>
              <span role="cell">—</span>
              <span role="cell">—</span>
              <span role="cell">—</span>
              <span role="cell">—</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

