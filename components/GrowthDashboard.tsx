'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { Product, ProductGrowthPayload, ProductGrowthSnapshot } from '@/lib/types';
import { formatNumber, getProductReelFarmCode } from '@/lib/utils';

function metricValue(value: unknown) {
  if (value === null || value === undefined) return '—';
  return formatNumber(value);
}

function GrowthDailyTable({ rows }: { rows: ProductGrowthSnapshot[] }) {
  return (
    <section className="growth-daily-card">
      <div className="growth-daily-head">
        <div>
          <h2>每日记录</h2>
          <p>按北京时间归档，每一行是一天的播放和 Onboarding Unique。</p>
        </div>
      </div>

      <div className="growth-daily-table-wrap">
        <table className="growth-daily-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>总播放</th>
              <th>ReelFarm</th>
              <th>Clone</th>
              <th>Onboarding Unique</th>
              <th>同步时间</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.slice().reverse().map(row => (
              <tr key={row.id || row.report_date}>
                <td>{row.report_date || '—'}</td>
                <td>{metricValue(row.total_views)}</td>
                <td>{metricValue(row.reelfarm_views)}</td>
                <td>{metricValue(row.clone_views)}</td>
                <td>{metricValue(row.onboarding_unique)}</td>
                <td>{row.synced_at ? row.synced_at.slice(0, 19).replace('T', ' ') : '—'}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={6}>暂无每日记录，先同步一次当前产品。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function GrowthDashboard({ products }: { products: Product[] }) {
  const [productId, setProductId] = useState('');
  const [payload, setPayload] = useState<ProductGrowthPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');

  const selectedProduct = useMemo(
    () => products.find(product => product.id === productId) || products[0] || null,
    [products, productId]
  );
  const productCode = selectedProduct ? getProductReelFarmCode(selectedProduct) : '';

  async function loadGrowth() {
    if (!productCode) return;
    setLoading(true);
    setError('');
    try {
      const next = await api.productGrowth(productCode, 30);
      setPayload(next);
    } catch (loadError: any) {
      setError(loadError?.message || '增长看板读取失败');
    } finally {
      setLoading(false);
    }
  }

  async function syncGrowth() {
    if (!productCode) return;
    setSyncing(true);
    setError('');
    try {
      await api.syncProductGrowth(productCode, 30);
      await loadGrowth();
    } catch (syncError: any) {
      setError(syncError?.message || '增长数据同步失败');
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    if (!productId && products[0]) setProductId(products[0].id);
  }, [products, productId]);

  useEffect(() => {
    loadGrowth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productCode]);

  const latest = payload?.latest || {};
  const cards = [
    { label: '昨日总播放量', value: latest.total_views, hint: `RF ${metricValue(latest.reelfarm_views)} · Clone ${metricValue(latest.clone_views)}` },
    { label: '昨日 Onboarding Unique', value: latest.onboarding_unique, hint: 'Mixpanel unique users · 按北京时间归档' }
  ];

  return (
    <section className="growth-page">
      <header className="growth-hero">
        <div>
          <p className="dashboard-kicker">Product Growth</p>
          <h1>Welcome to Deca Growth</h1>
          <p>统一用北京时间看业务表现，数据源保留各自原始时区。</p>
        </div>
        <div className="growth-actions">
          <select value={selectedProduct?.id || ''} onChange={event => setProductId(event.target.value)}>
            {products.map(product => (
              <option value={product.id} key={product.id}>{product.name}</option>
            ))}
          </select>
          <button type="button" onClick={syncGrowth} disabled={syncing || !productCode}>{syncing ? '同步中...' : '同步最近 30 天'}</button>
        </div>
      </header>

      {error ? <div className="growth-error">{error}</div> : null}
      {loading ? <div className="growth-loading">正在读取增长快照...</div> : null}

      <div className="growth-metric-grid">
        {cards.map(card => (
          <article className="growth-metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{metricValue(card.value)}</strong>
            <small>{card.hint}</small>
          </article>
        ))}
      </div>

      <GrowthDailyTable rows={payload?.series || []} />

      <section className="growth-source-card">
        <h2>Time Strategy</h2>
        <div className="growth-source-grid">
          <div>
            <span>看板口径</span>
            <strong>{payload?.report_timezone || 'Asia/Shanghai'}</strong>
            <p>团队统一按北京时间看每日数据。</p>
          </div>
          <div>
            <span>Mixpanel 源口径</span>
            <strong>{payload?.source_timezone || 'America/Los_Angeles'}</strong>
            <p>同步时按 PDT 项目日期拉取，再归档为北京时间 report date。</p>
          </div>
          <div>
            <span>播放源</span>
            <strong>ReelFarm + Museon Clone</strong>
            <p>两边都从本地关系型数据库读取，不在看板打开时实时调用第三方。</p>
          </div>
        </div>
      </section>
    </section>
  );
}
