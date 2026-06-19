import { getTagCategory } from '@/lib/tagUtils';
import { formatNumber, getCountryReelFarmCode } from '@/lib/utils';
import type { AccountTagRow, TagFilterRow } from './CountryAccountTagHelpers';

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

export function getAccountPoolTagOptions(productTagOptions: string[], rows: AccountPoolRow[]) {
  return Array.from(new Set([
    ...productTagOptions,
    ...rows.flatMap(row => row.tags || [])
  ])).filter(Boolean).sort((a, b) => a.localeCompare(b));
}

export function filterAccountPoolRows({
  rows,
  search,
  countryFilter,
  statusFilter,
  publishMethodFilter,
  tagFilters,
  dataSource
}: {
  rows: AccountPoolRow[];
  search: string;
  countryFilter: string;
  statusFilter: string;
  publishMethodFilter: string;
  tagFilters: TagFilterRow[];
  dataSource: AccountPoolDataSource;
}) {
  const query = search.trim().toLowerCase();
  const activeTagFilters = tagFilters.filter(filter => filter.category && filter.tags.length);
  return rows.filter(row => {
    const username = String(row.username || row.display_name || row.account_id || '').toLowerCase();
    const countryCode = getCountryReelFarmCode(row.country);
    const status = String(row.status || 'unknown').toLowerCase();
    const publishMethod = getPublishMethod(row, dataSource);
    if (query && !username.includes(query)) return false;
    if (countryFilter !== 'all' && countryCode !== countryFilter) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    if (publishMethodFilter !== 'all' && publishMethod !== publishMethodFilter) return false;
    if (activeTagFilters.length) {
      const rowTags = row.tags || [];
      const matchesTags = activeTagFilters.every(filter => {
        const selected = new Set(filter.tags);
        return rowTags.some(tag => getTagCategory(tag) === filter.category && selected.has(tag));
      });
      if (!matchesTags) return false;
    }
    return true;
  });
}

export function sortAccountPoolRows(rows: AccountPoolRow[], viewSort: ViewSortDirection) {
  if (viewSort === 'none') return rows;
  return [...rows].sort((left, right) => {
    const leftViews = getAccountAvgViews(left);
    const rightViews = getAccountAvgViews(right);
    if (leftViews === rightViews) {
      return String(left.username || left.display_name || left.account_id || '')
        .localeCompare(String(right.username || right.display_name || right.account_id || ''));
    }
    return viewSort === 'desc' ? rightViews - leftViews : leftViews - rightViews;
  });
}
