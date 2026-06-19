import type { BusinessMaterialReportRow } from './types';
import { formatNumber } from './utils';

export function metric(value: unknown) {
  if (value === null || value === undefined) return '—';
  return formatNumber(value);
}

export function percent(value: unknown) {
  if (value === null || value === undefined) return '—';
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number.toFixed(2)}%`;
}

export function dateOnly(value?: string) {
  return String(value || '').slice(0, 10) || '—';
}

export function metricDetail(count?: unknown, views?: unknown) {
  return `${metric(count)} posts · ${metric(views)} views`;
}

export function numberValue(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function coverage(row: BusinessMaterialReportRow) {
  return `${metric(row.reelfarm_published_automations)} / ${metric(row.reelfarm_expected_automations)}`;
}
