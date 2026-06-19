import type { DailyFeishuReport } from './types';
import { formatNumber } from './utils';

export const DEFAULT_LLM_MODEL = 'gpt-4.1-mini';

export const FALLBACK_MODEL_OPTIONS = [
  'gpt-5',
  'gpt-5-mini',
  'gpt-5-nano',
  'gpt-4.1',
  'gpt-4.1-mini',
  'gpt-4.1-nano',
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-4'
];

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
