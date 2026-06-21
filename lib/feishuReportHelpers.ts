import type { DailyFeishuReport } from './types';
import { formatNumber } from './utils';

export function localIsoDate(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function ratio(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return number;
}

export function reportTotals(report?: DailyFeishuReport | null) {
  return report?.totals || {};
}

export function formatFeishuMetric(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return formatNumber(value);
}
