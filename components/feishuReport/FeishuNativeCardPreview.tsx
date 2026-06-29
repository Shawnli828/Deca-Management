'use client';

import type { FeishuCardData } from '@/lib/types';
import { FeishuOverviewPanel } from './FeishuOverviewPanel';
import { FeishuProductPreviewPanel } from './FeishuProductPanel';

export function FeishuNativeCardPreview({ data, loading }: { data: FeishuCardData | null; loading: boolean }) {
  if (!data) {
    return (
      <section className="feishu-native-preview">
        <div className="feishu-native-empty">{loading ? '正在生成飞书卡片预览...' : '暂无飞书卡片预览'}</div>
      </section>
    );
  }

  return (
    <section className="feishu-native-preview">
      <div className="feishu-native-dashboard">
        <FeishuOverviewPanel data={data} />
        <FeishuProductPreviewPanel products={data.products || []} countryAvgTrend={data.countryAvgTrend || {}} />
      </div>
    </section>
  );
}
