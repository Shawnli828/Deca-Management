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

export function businessWindowText(row: BusinessMaterialReportRow) {
  const start = row.business_window_local?.start;
  const end = row.business_window_local?.end;
  if (!start || !end) return '—';
  return `${start.slice(0, 16).replace('T', ' ')} → ${end.slice(0, 16).replace('T', ' ')}`;
}

export function downloadRate(downloads: unknown, views: unknown) {
  const downloadCount = Number(downloads || 0);
  const viewCount = Number(views || 0);
  if (!viewCount) return null;
  return (downloadCount / viewCount) * 100;
}
