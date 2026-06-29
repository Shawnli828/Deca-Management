'use client';

import type { FeishuGrowthSyncResult, FeishuSourceSyncResult } from '@/hooks/useFeishuReport';
import type {
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult
} from '@/lib/types';
import { FeishuNativeCardPreview } from './FeishuNativeCardPreview';

export function FeishuReportLayout({
  payload,
  loading
}: {
  payload: DailyFeishuPreviewPayload | null;
  loading: boolean;
}) {
  const showCardPreview = Boolean(payload?.card_data);
  return showCardPreview ? <FeishuNativeCardPreview data={payload?.card_data || null} loading={loading} /> : null;
}

export function FeishuStatusMessages({
  error,
  payload,
  sendResult,
  growthSyncResult,
  sourceSyncResult
}: {
  error: string;
  payload: DailyFeishuPreviewPayload | null;
  sendResult: DailyFeishuSendResult | null;
  growthSyncResult: FeishuGrowthSyncResult | null;
  sourceSyncResult: FeishuSourceSyncResult | null;
}) {
  const syncPlan = payload?.report?.sync_status?.sync_plan;
  const growthCodes = syncPlan?.growth_product_codes || [];
  const feishuCodes = syncPlan?.feishu_product_codes || [];

  return (
    <>
      {error ? <div className="growth-error">{error}</div> : null}
      {(growthCodes.length || feishuCodes.length) ? (
        <div className="feishu-sync-plan">
          同步计划：Growth {growthCodes.join(' / ') || '—'} · Feishu {feishuCodes.join(' / ') || '—'}
        </div>
      ) : null}
      {sourceSyncResult ? (
        <div className={sourceSyncResult.ok ? 'feishu-success' : 'feishu-sync-partial'}>
          RF / Museon 同步{sourceSyncResult.ok ? '完成' : '未完成'}
          {sourceSyncResult.reelfarm ? `：RF ${sourceSyncResult.reelfarm.records_count || 0} 条` : ''}
          {sourceSyncResult.museon ? ` · Museon ${sourceSyncResult.museon.records_count || 0} 条` : ''}
          {sourceSyncResult.error ? ` · ${sourceSyncResult.error}` : ''}
        </div>
      ) : null}
      {growthSyncResult?.products.length ? (
        <div className={growthSyncResult.ok ? 'feishu-success' : 'feishu-sync-partial'}>
          Mixpanel 缓存同步完成：{growthSyncResult.products.map(item => `${item.productCode} ${item.count} 条快照`).join(' · ')}
          {growthSyncResult.errors.length ? ` · 失败 ${growthSyncResult.errors.length} 个产品` : ''}
        </div>
      ) : null}
      {sendResult?.ok ? (
        <div className="feishu-success">
          已发送到飞书：{sendResult.sent_at || '刚刚'}
          {sendResult.mode ? ` · ${
            sendResult.mode === 'image'
              ? 'SVG 图片看板'
              : sendResult.mode === 'template'
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
