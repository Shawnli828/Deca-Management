import { formatFeishuMetric } from '@/lib/feishuReportHelpers';
import type { FeishuCardData } from '@/lib/types';

export type FeishuProductCardData = NonNullable<FeishuCardData['products']>[number];

export function cardMetric(value: unknown) {
  return formatFeishuMetric(value);
}

export function cardRate(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${formatFeishuMetric(value)}%`;
  return `${numeric.toFixed(2)}%`;
}

export function postCoverage(product: { rfPublished?: number; rfExpected?: number }) {
  return `${cardMetric(product.rfPublished)}/${cardMetric(product.rfExpected)}`;
}

export function productKey(product?: FeishuProductCardData) {
  return String(product?.code || product?.name || '').trim().toUpperCase();
}

export function productInitials(product?: FeishuProductCardData) {
  const code = String(product?.code || '').trim().toUpperCase();
  if (code) return code.slice(0, 3);
  const label = String(product?.name || product?.code || 'P').trim();
  const parts = label.split(/[\s_-]+/).filter(Boolean);
  if (parts.length > 1) return parts.map(part => part[0]).join('').slice(0, 2).toUpperCase();
  return label.slice(0, 2).toUpperCase();
}

