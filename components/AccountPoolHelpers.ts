import { formatNumber } from '@/lib/utils';
import type { AccountTagRow } from './CountryAccountTagHelpers';

export type AccountPoolRow = AccountTagRow;
export type ViewSortDirection = 'none' | 'desc' | 'asc';
export type AccountPoolDataSource = 'reelfarm' | 'museon_clone';

export function getAccountAvgViews(row: AccountPoolRow) {
  const posts = Number(row.post_count) || 0;
  if (!posts) return 0;
  return Math.round((Number(row.total_views) || 0) / posts);
}

export function getAutomationDisplay(row: AccountPoolRow, dataSource: AccountPoolDataSource) {
  const names = String(row.automation_names || row.automation_name || '').trim();
  if (names) return names;
  return dataSource === 'museon_clone' ? 'api' : 'rpa';
}

export function getPublishMethod(row: AccountPoolRow, dataSource: AccountPoolDataSource) {
  const storedMethod = String(row.publish_method || '').trim().toLowerCase();
  if (['manual', 'api', 'rpa'].includes(storedMethod)) return storedMethod;

  const postMode = String(row.post_mode || '').trim().toUpperCase();
  if (postMode === 'MEDIA_UPLOAD') return 'manual';
  if (postMode === 'DIRECT_POST') return 'api';
  if (postMode === 'RPA') return 'rpa';

  const sourceText = [
    row.data_source,
    row.automation_names,
    row.automation_name,
    row.campaign_name
  ].filter(Boolean).join(' ').toLowerCase();
  if (sourceText.includes('manual')) return 'manual';
  if (sourceText.includes('api') || sourceText.includes('museon')) return 'api';
  if (sourceText.includes('rpa') || sourceText.includes('reelfarm')) return 'rpa';
  return dataSource === 'museon_clone' ? 'api' : 'rpa';
}

export function getAccountRowKey(row: AccountPoolRow, dateFrom: string, dateTo: string) {
  return `${row.country.id}:${row.account_id}:${dateFrom || 'start'}:${dateTo || 'end'}`;
}

export function getAccountPoolPerformanceMetrics(filteredRows: AccountPoolRow[]) {
  const hasAccountCoverageFields = filteredRows.some(
    row => row.posted_account_count !== undefined || row.expected_account_count !== undefined
  );
  const postedAccounts = hasAccountCoverageFields
    ? filteredRows.reduce((sum, row) => sum + (Number(row.posted_account_count) || 0), 0)
    : filteredRows.filter(row => (Number(row.post_count) || 0) > 0).length;
  const expectedAccounts = hasAccountCoverageFields
    ? filteredRows.reduce((sum, row) => sum + (Number(row.expected_account_count) || 0), 0)
    : filteredRows.length;
  const posts = filteredRows.reduce((sum, row) => sum + (Number(row.post_count) || 0), 0);
  const views = filteredRows.reduce((sum, row) => sum + (Number(row.total_views) || 0), 0);
  const likes = filteredRows.reduce((sum, row) => sum + (Number(row.total_likes) || 0), 0);
  const comments = filteredRows.reduce((sum, row) => sum + (Number(row.total_comments) || 0), 0);
  const shares = filteredRows.reduce((sum, row) => sum + (Number(row.total_shares) || 0), 0);
  const avgViews = posts ? Math.round(views / posts) : 0;
  const engagement = views ? ((likes + comments + shares) / views) * 100 : 0;

  return [
    { label: 'POSTED', value: `${formatNumber(postedAccounts)}/${formatNumber(expectedAccounts)}`, note: 'Posted accounts / expected active accounts' },
    { label: 'POSTS', value: formatNumber(posts) },
    { label: 'VIEWS', value: formatNumber(views) },
    { label: 'AVG VIEWS', value: formatNumber(avgViews), note: 'Filtered total views / filtered posts' },
    { label: 'LIKES', value: formatNumber(likes) },
    { label: 'COMMENTS', value: formatNumber(comments) },
    { label: 'SHARES', value: formatNumber(shares) },
    { label: 'ENGAGEMENT', value: `${engagement.toFixed(2)}%`, note: '(Likes + comments + shares) / views' }
  ];
}
