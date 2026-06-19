'use client';

import { coverage, dateOnly, metric, metricDetail, percent } from '@/lib/businessReportFormatters';
import type { BusinessMaterialReportPayload, BusinessMaterialReportRow, Product } from '@/lib/types';

type BusinessSummaryCard = {
  label: string;
  value: string;
  meta: string;
};

export function BusinessReportSummaryGrid({ cards }: { cards: BusinessSummaryCard[] }) {
  return (
    <div className="business-report-summary">
      {cards.map(card => (
        <article key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.meta}</small>
        </article>
      ))}
    </div>
  );
}

export function BusinessReportTable({
  rows,
  payload,
  selectedProduct,
  productCode
}: {
  rows: BusinessMaterialReportRow[];
  payload: BusinessMaterialReportPayload | null;
  selectedProduct: Product | null;
  productCode: string;
}) {
  return (
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
  );
}
