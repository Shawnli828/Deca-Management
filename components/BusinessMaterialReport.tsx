'use client';

import { BusinessReportControls } from '@/components/BusinessReportControls';
import { BusinessReportSummaryGrid, BusinessReportTable } from '@/components/BusinessMaterialReportParts';
import { WorkspaceHeader } from '@/components/dashboard/WorkspaceHeader';
import { useBusinessMaterialReport } from '@/hooks/useBusinessMaterialReport';
import { metric, metricDetail, numberValue, percent } from '@/lib/businessReportFormatters';
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
      <WorkspaceHeader
        className="business-report-head"
        kicker="Daily Metric"
        title="Daily Metric"
        description="内容按北京时间 23:59 到次日 23:59 归属；Onboarding 按前一天 08:00 到当天 08:00 统计。"
        actions={(
          <BusinessReportControls
            products={products}
            selectedProductId={selectedProduct?.id || ''}
            days={days}
            customRange={customRange}
            dateFrom={dateFrom}
            dateTo={dateTo}
            loading={loading}
            productCode={productCode}
            onProductChange={setProductId}
            onDaysChange={setDays}
            onDateFromChange={setDateFrom}
            onDateToChange={setDateTo}
            onApply={loadReport}
          />
        )}
      />

      {error ? <div className="growth-error">{error}</div> : null}
      {loading ? <div className="growth-loading">正在读取业务日数据...</div> : null}

      <BusinessReportSummaryGrid cards={summaryCards} />
      <BusinessReportTable rows={rows} payload={payload} selectedProduct={selectedProduct} productCode={productCode} />
    </section>
  );
}
