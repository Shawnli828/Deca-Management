'use client';

import { businessIsoDate, useBusinessMaterialReport } from '@/hooks/useBusinessMaterialReport';
import { businessWindowText, downloadRate, metric, percent } from '@/lib/businessReportFormatters';
import type { Product } from '@/lib/types';

export function GrowthDashboard({ products }: { products: Product[] }) {
  const {
    days,
    setDays,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    payload,
    loading,
    error,
    selectedProduct,
    productCode,
    customRange,
    loadReport: loadGrowth,
    setProductId
  } = useBusinessMaterialReport({
    products,
    errorMessage: 'Growth 看板读取失败'
  });

  const rows = payload?.rows || [];
  const totals = payload?.totals || {};
  const totalRate = downloadRate(totals.downloads, totals.total_views);
  const summaryCards = [
    {
      label: '新增播放',
      value: metric(totals.total_views),
      meta: `RF ${metric(totals.reelfarm_views)} · Clone ${metric(totals.clone_views)}`
    },
    {
      label: 'Onboarding Unique',
      value: metric(totals.downloads),
      meta: 'Mixpanel unique onboarding'
    },
    {
      label: '有增长 Posts',
      value: metric(totals.total_posts),
      meta: `RF ${metric(totals.reelfarm_materials)} · Clone ${metric(totals.clone_materials)}`
    },
    {
      label: '下载 / 播放',
      value: percent(totalRate),
      meta: 'Onboarding Unique / 新增播放'
    }
  ];

  return (
    <section className="business-report-page">
      <header className="business-report-head">
        <div>
          <p className="dashboard-kicker">Growth 情况</p>
          <h1>Growth 情况</h1>
          <p>按北京时间 23:59 → 23:59 归档，播放量使用每日快照差值计算。</p>
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
          <input type="date" value={dateFrom} max={dateTo || businessIsoDate()} onChange={event => setDateFrom(event.target.value)} />
          <input type="date" value={dateTo} min={dateFrom || undefined} max={businessIsoDate()} onChange={event => setDateTo(event.target.value)} />
          <button type="button" onClick={loadGrowth} disabled={loading || !productCode}>{loading ? '读取中...' : '应用'}</button>
        </div>
      </header>

      {error ? <div className="growth-error">{error}</div> : null}
      {loading ? <div className="growth-loading">正在读取业务日增量...</div> : null}

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
            <h2>{selectedProduct?.name || productCode} · 每日增长记录</h2>
            <p>{payload?.date_from || '—'} 至 {payload?.date_to || '—'} · {payload?.report_timezone || 'Asia/Shanghai'}</p>
          </div>
        </div>
        <div className="business-report-table-wrap">
          <table className="business-report-table growth-increment-table">
            <thead>
              <tr>
                <th>业务日</th>
                <th>北京时间窗口</th>
                <th>RF 新增播放</th>
                <th>Clone 新增播放</th>
                <th>总新增播放</th>
                <th>Onboarding Unique</th>
                <th>下载/播放</th>
                <th>有增长 Posts</th>
              </tr>
            </thead>
            <tbody>
              {rows.length ? rows.slice().reverse().map(row => (
                <tr key={row.report_date}>
                  <td><strong>{row.report_date}</strong></td>
                  <td>{businessWindowText(row)}</td>
                  <td>{metric(row.reelfarm_views)}</td>
                  <td>{metric(row.clone_views)}</td>
                  <td><strong>{metric(row.total_views)}</strong></td>
                  <td><strong>{metric(row.downloads)}</strong></td>
                  <td>{percent(row.download_rate)}</td>
                  <td>{metric(row.total_posts)}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={8}>这个 range 暂时没有增长记录。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
