'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { BusinessMaterialReportPayload, BusinessMaterialReportRow, Product } from '@/lib/types';
import { formatNumber, getProductReelFarmCode } from '@/lib/utils';

function metric(value: unknown) {
  if (value === null || value === undefined) return '—';
  return formatNumber(value);
}

function percent(value: unknown) {
  if (value === null || value === undefined) return '—';
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number.toFixed(2)}%`;
}

function dateOnly(value?: string) {
  return String(value || '').slice(0, 10) || '—';
}

function compactWindow(window?: { start?: string; end?: string }) {
  const start = window?.start;
  const end = window?.end;
  if (!start || !end) return '—';
  return `${start.slice(5, 16).replace('T', ' ')} → ${end.slice(5, 16).replace('T', ' ')}`;
}

function metricDetail(count?: unknown, views?: unknown) {
  return `${metric(count)} posts · ${metric(views)} views`;
}

function coverage(row: BusinessMaterialReportRow) {
  return `${metric(row.reelfarm_published_automations)} / ${metric(row.reelfarm_expected_automations)}`;
}

function isoDate(offset = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

export function BusinessMaterialReport({ products }: { products: Product[] }) {
  const [productId, setProductId] = useState('');
  const [days, setDays] = useState(7);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [payload, setPayload] = useState<BusinessMaterialReportPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedProduct = useMemo(
    () => products.find(product => product.id === productId) || products[0] || null,
    [products, productId]
  );
  const productCode = selectedProduct ? getProductReelFarmCode(selectedProduct) : '';
  const customRange = Boolean(dateFrom || dateTo);

  async function loadReport() {
    if (!productCode) return;
    setLoading(true);
    setError('');
    try {
      const next = await api.businessMaterialReport(productCode, {
        days,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        mode: 'published_materials'
      });
      setPayload(next);
    } catch (loadError: any) {
      setError(loadError?.message || '业务日表读取失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!productId && products[0]) setProductId(products[0].id);
  }, [products, productId]);

  useEffect(() => {
    loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productCode, days]);

  const rows = payload?.rows || [];
  const totals = payload?.totals || {};
  const totalDownloadRate = Number(totals.total_views || 0)
    ? (Number(totals.downloads || 0) / Number(totals.total_views || 1)) * 100
    : null;
  const summaryCards = [
    {
      label: 'RF 发布覆盖',
      value: `${metric(totals.reelfarm_published_automations)} / ${metric(totals.reelfarm_expected_automations)}`,
      meta: '有发布记录的 RF automation / active automation'
    },
    {
      label: 'ReelFarm 均播',
      value: metric(totals.reelfarm_avg_views),
      meta: metricDetail(totals.reelfarm_posts, totals.reelfarm_views)
    },
    {
      label: 'Clone 均播',
      value: metric(totals.clone_avg_views),
      meta: metricDetail(totals.clone_posts, totals.clone_views)
    },
    {
      label: 'Onboarding Unique',
      value: metric(totals.downloads),
      meta: `下载 / 播放 ${percent(totalDownloadRate)}`
    }
  ];

  return (
    <section className="business-report-page">
      <header className="business-report-head">
        <div>
          <p className="dashboard-kicker">Daily Metric</p>
          <h1>Daily Metric</h1>
          <p>内容按北京时间 23:59 到次日 23:59 归属；Onboarding 按前一天 08:00 到当天 08:00 统计。</p>
        </div>
        <div className="business-report-controls">
          <select value={selectedProduct?.id || ''} onChange={event => setProductId(event.target.value)}>
            {products.map(product => (
              <option value={product.id} key={product.id}>{product.name}</option>
            ))}
          </select>
          <div className="business-report-preset" aria-label="业务日范围">
            {[7, 14, 30].map(value => (
              <button
                className={!customRange && days === value ? 'active' : ''}
                type="button"
                onClick={() => {
                  setDays(value);
                  setDateFrom('');
                  setDateTo('');
                }}
                key={value}
              >
                {value} 天
              </button>
            ))}
          </div>
          <input type="date" value={dateFrom} max={dateTo || isoDate()} onChange={event => setDateFrom(event.target.value)} />
          <input type="date" value={dateTo} min={dateFrom || undefined} max={isoDate()} onChange={event => setDateTo(event.target.value)} />
          <button type="button" onClick={loadReport} disabled={loading || !productCode}>{loading ? '读取中...' : '应用'}</button>
        </div>
      </header>

      {error ? <div className="growth-error">{error}</div> : null}
      {loading ? <div className="growth-loading">正在读取业务日数据...</div> : null}

      <div className="business-report-summary">
        {summaryCards.map(card => (
          <article key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <small>{card.meta}</small>
          </article>
        ))}
      </div>

      <section className="business-report-table-card">
        <div className="business-report-table-title">
          <div>
            <h2>{selectedProduct?.name || productCode} · 业务日明细</h2>
            <p>{payload?.date_from || '—'} 至 {payload?.date_to || '—'} · {payload?.report_timezone || 'Asia/Shanghai'}</p>
          </div>
        </div>
        <div className="business-report-table-wrap">
          <table className="business-report-table">
            <thead>
              <tr>
                <th>业务日</th>
                <th>内容窗口</th>
                <th>Onboarding 窗口</th>
                <th>RF 发布覆盖</th>
                <th>ReelFarm 均播</th>
                <th>Clone 均播</th>
                <th>总播放</th>
                <th>Onboarding</th>
                <th>下载/播放</th>
              </tr>
            </thead>
            <tbody>
              {rows.length ? rows.slice().reverse().map(row => (
                <tr key={row.report_date}>
                  <td><strong>{dateOnly(row.report_date)}</strong></td>
                  <td>
                    <span className="window-cell">{compactWindow(row.business_window_local)}</span>
                  </td>
                  <td>
                    <span className="window-cell">{compactWindow(row.onboarding_window_local)}</span>
                  </td>
                  <td>
                    <span className="coverage-pill">{coverage(row)}</span>
                    <small className="metric-sub">发布账号 / 应发账号</small>
                  </td>
                  <td>
                    <span className="metric-stack">
                      <strong className="metric-main">{metric(row.reelfarm_avg_views)}</strong>
                      <small className="metric-sub">{metricDetail(row.reelfarm_posts, row.reelfarm_views)}</small>
                    </span>
                  </td>
                  <td>
                    <span className="metric-stack">
                      <strong className="metric-main">{metric(row.clone_avg_views)}</strong>
                      <small className="metric-sub">{metricDetail(row.clone_posts, row.clone_views)}</small>
                    </span>
                  </td>
                  <td><strong className="total-views-cell">{metric(row.total_views)}</strong></td>
                  <td><strong className="download-cell">{metric(row.downloads)}</strong></td>
                  <td><span className="rate-cell">{percent(row.download_rate)}</span></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={9}>这个 range 暂时没有业务日数据。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
