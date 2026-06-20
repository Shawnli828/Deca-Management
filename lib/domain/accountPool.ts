import { getTagCategory } from '../tagUtils';
import { formatNumber, getCountryReelFarmCode } from '../utils';
import type { AccountTagRow, TagFilterRow } from './accountTags';

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
  let postedAccounts = 0;
  let expectedAccounts = hasAccountCoverageFields ? 0 : filteredRows.length;
  let posts = 0;
  let views = 0;
  let likes = 0;
  let comments = 0;
  let shares = 0;

  for (const row of filteredRows) {
    const rowPosts = Number(row.post_count) || 0;
    posts += rowPosts;
    views += Number(row.total_views) || 0;
    likes += Number(row.total_likes) || 0;
    comments += Number(row.total_comments) || 0;
    shares += Number(row.total_shares) || 0;

    if (hasAccountCoverageFields) {
      postedAccounts += Number(row.posted_account_count) || 0;
      expectedAccounts += Number(row.expected_account_count) || 0;
    } else if (rowPosts > 0) {
      postedAccounts += 1;
    }
  }

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
  const activeTagFilters = tagFilters
    .filter(filter => filter.category && filter.tags.length)
    .map(filter => ({
      category: filter.category,
      tags: new Set(filter.tags)
    }));
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
        return rowTags.some(tag => getTagCategory(tag) === filter.category && filter.tags.has(tag));
      });
      if (!matchesTags) return false;
    }
    return true;
  });
}

export function sortAccountPoolRows(rows: AccountPoolRow[], viewSort: ViewSortDirection) {
  if (viewSort === 'none') return rows;
  return rows
    .map(row => ({
      row,
      avgViews: getAccountAvgViews(row),
      label: String(row.username || row.display_name || row.account_id || '')
    }))
    .sort((left, right) => {
      if (left.avgViews === right.avgViews) {
        return left.label.localeCompare(right.label);
      }
      return viewSort === 'desc' ? right.avgViews - left.avgViews : left.avgViews - right.avgViews;
    })
    .map(item => item.row);
}
