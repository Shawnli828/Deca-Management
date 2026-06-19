'use client';

import { businessIsoDate, useBusinessMaterialReport } from '@/hooks/useBusinessMaterialReport';
import { coverage, dateOnly, metric, metricDetail, numberValue, percent } from '@/lib/businessReportFormatters';
import type { Product } from '@/lib/types';

export function BusinessMaterialReport({ products }: { products: Product[] }) {
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
    loadReport,
    setProductId
  } = useBusinessMaterialReport({
    products,
    mode: 'published_materials',
    errorMessage: '业务日表读取失败'
  });

  const rows = payload?.rows || [];
  const totals = payload?.totals || {};
  const reportDayCount = rows.length;
  const rangeLabel = customRange ? '自定义日' : `${days}日`;
  const averageDailyViews = reportDayCount
    ? rows.reduce((sum, row) => sum + numberValue(row.total_views), 0) / reportDayCount
    : null;
  const onboardingRows = rows.filter(row => row.downloads !== null && row.downloads !== undefined);
  const averageOnboarding = onboardingRows.length
    ? onboardingRows.reduce((sum, row) => sum + numberValue(row.downloads), 0) / onboardingRows.length
    : null;
  const totalDownloadRate = Number(totals.total_views || 0)
    ? (Number(totals.downloads || 0) / Number(totals.total_views || 1)) * 100
    : null;
  const summaryCards = [
    {
      label: '每日总播放均值',
      value: metric(averageDailyViews),
      meta: `${rangeLabel}平均 · ${metric(totals.total_views)} 总播放`
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
      label: 'Onboarding Unique 均值',
      value: metric(averageOnboarding),
      meta: `均转化 ${percent(totalDownloadRate)}`
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
          <input type="date" value={dateFrom} max={dateTo || businessIsoDate()} onChange={event => setDateFrom(event.target.value)} />
          <input type="date" value={dateTo} min={dateFrom || undefined} max={businessIsoDate()} onChange={event => setDateTo(event.target.value)} />
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
                  <td colSpan={7}>这个 range 暂时没有业务日数据。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
