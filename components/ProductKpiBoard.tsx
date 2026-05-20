'use client';

import type { ProductKpis } from '@/lib/types';
import { formatNumber, formatPercent } from '@/lib/utils';

export function ProductKpiBoard({ kpis }: { kpis?: ProductKpis | null }) {
  const todayAverageViews = Number(kpis?.today?.average_views) || 0;
  const sevenAverageViews = Number(kpis?.seven_day?.average_views) || 0;
  const sevenAverageEr = Number(kpis?.seven_day?.average_er) || 0;

  return (
    <div className="product-kpi-board">
      <div className="product-kpi-card today">
        <span>当日均播</span>
        <strong>{formatNumber(todayAverageViews)}</strong>
      </div>
      <div className="product-kpi-card views">
        <span>过去 7 日均播</span>
        <strong>{formatNumber(sevenAverageViews)}</strong>
      </div>
      <div className="product-kpi-card er">
        <span>过去 7 日平均 ER</span>
        <strong>{formatPercent(sevenAverageEr)}</strong>
      </div>
    </div>
  );
}
