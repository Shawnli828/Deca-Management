import assert from 'node:assert/strict';
import {
  type AccountPoolRow,
  filterAccountPoolRows,
  getAccountAvgViews,
  getAccountPoolPerformanceMetrics,
  getAccountPoolTagOptions,
  getAccountRowKey,
  getAutomationDisplay,
  getPublishMethod,
  sortAccountPoolRows
} from '../lib/domain/accountPool';
import type { Country } from '../lib/types';

const germany: Country = { id: 'country-ge', name: 'Germany', reelFarmCode: 'GE' };
const unitedStates: Country = { id: 'country-us', name: 'United States', reelFarmCode: 'US' };

const rows: AccountPoolRow[] = [
  {
    account_id: 'account-demi-ge',
    username: 'demi_ge',
    display_name: 'Demi GE',
    country: germany,
    status: 'active',
    automation_names: 'GE-DM-topic-format',
    publish_method: 'api',
    post_count: 4,
    total_views: 1200,
    total_likes: 120,
    total_comments: 30,
    total_shares: 10,
    posted_account_count: 1,
    expected_account_count: 1,
    tags: ['Stage: Hero', 'Format: Slides'],
    issues: ['Missing avatar']
  },
  {
    account_id: 'account-demi-us',
    username: 'demi_us',
    display_name: 'Demi US',
    country: unitedStates,
    status: 'paused',
    post_mode: 'MEDIA_UPLOAD',
    post_count: 2,
    total_views: 300,
    total_likes: 15,
    total_comments: 3,
    total_shares: 2,
    posted_account_count: 0,
    expected_account_count: 1,
    tags: ['Stage: Testing']
  }
];

assert.equal(getAccountAvgViews(rows[0]), 300, 'average views should use total views divided by posts');
assert.equal(getPublishMethod(rows[0], 'reelfarm'), 'api', 'stored publish method should win');
assert.equal(getPublishMethod(rows[1], 'reelfarm'), 'manual', 'MEDIA_UPLOAD should map to manual');
assert.equal(getAutomationDisplay(rows[1], 'museon_clone'), 'api', 'clone rows without automation names should default to api');
assert.equal(
  getAccountRowKey(rows[0], '2026-06-13', '2026-06-19'),
  'country-ge:account-demi-ge:2026-06-13:2026-06-19',
  'row key should include country, account, and date range'
);

const filtered = filterAccountPoolRows({
  rows,
  search: 'ge',
  countryFilter: 'GE',
  statusFilter: 'active',
  publishMethodFilter: 'api',
  tagFilters: [{ id: 'filter-stage', category: 'Stage', tags: ['Stage: Hero'] }],
  dataSource: 'reelfarm'
});
assert.deepEqual(filtered.map(row => row.account_id), ['account-demi-ge'], 'filters should combine search, country, status, publish method, and tags');

assert.deepEqual(
  sortAccountPoolRows(rows, 'asc').map(row => row.account_id),
  ['account-demi-us', 'account-demi-ge'],
  'ascending avg view sort should put lower average first'
);
assert.deepEqual(
  sortAccountPoolRows(rows, 'desc').map(row => row.account_id),
  ['account-demi-ge', 'account-demi-us'],
  'descending avg view sort should put higher average first'
);

assert.deepEqual(
  getAccountPoolTagOptions(['Stage: Hero', 'Quality: New'], rows),
  ['Format: Slides', 'Quality: New', 'Stage: Hero', 'Stage: Testing'],
  'tag options should merge product tags and row tags without duplicates'
);

const metrics = Object.fromEntries(getAccountPoolPerformanceMetrics(rows).map(item => [item.label, item.value]));
assert.equal(metrics.POSTED, '1/2', 'coverage metric should use posted and expected account fields');
assert.equal(metrics.POSTS, '6', 'posts metric should sum rows');
assert.equal(metrics.VIEWS, '1.5K', 'views metric should format summed views');
assert.equal(metrics['AVG VIEWS'], '250', 'average views metric should use filtered total views divided by filtered posts');
assert.equal(metrics.ENGAGEMENT, '12.00%', 'engagement should include likes, comments, and shares over views');

console.log('account pool regression checks passed');
