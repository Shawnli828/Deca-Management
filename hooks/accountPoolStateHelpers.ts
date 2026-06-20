import { api } from '@/lib/api';
import type { AccountPoolDataSource, AccountPoolRow } from '@/lib/domain/accountPool';
import type { TagFilterRow } from '@/lib/domain/accountTags';
import type { AccountSummary, Country } from '@/lib/types';
import { getCountryReelFarmCode } from '@/lib/utils';

export type AccountPoolAccount = AccountSummary & { country: Country };

export function addAccountPoolDateFilters(params: URLSearchParams, dateFrom: string, dateTo: string) {
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);
  return params;
}

export function buildAccountPoolQueryParams({
  productCode,
  country,
  dateFrom,
  dateTo,
  dataSource
}: {
  productCode: string;
  country: Country;
  dateFrom: string;
  dateTo: string;
  dataSource: AccountPoolDataSource;
}) {
  const params = addAccountPoolDateFilters(new URLSearchParams({
    resource: 'accounts',
    product_code: productCode,
    country_code: getCountryReelFarmCode(country)
  }), dateFrom, dateTo);
  if (dataSource !== 'reelfarm') params.set('source', dataSource);
  return params;
}

export function buildProductAccountPoolQueryParams({
  productCode,
  dateFrom,
  dateTo,
  dataSource
}: {
  productCode: string;
  dateFrom: string;
  dateTo: string;
  dataSource: AccountPoolDataSource;
}) {
  const params = addAccountPoolDateFilters(new URLSearchParams({
    resource: 'accounts',
    product_code: productCode
  }), dateFrom, dateTo);
  if (dataSource !== 'reelfarm') params.set('source', dataSource);
  return params;
}

export function buildAccountPostsQueryParams({
  productCode,
  country,
  accountId,
  limit,
  offset,
  dateFrom,
  dateTo,
  dataSource
}: {
  productCode: string;
  country: Country;
  accountId: string;
  limit: number;
  offset: number;
  dateFrom: string;
  dateTo: string;
  dataSource: AccountPoolDataSource;
}) {
  const params = addAccountPoolDateFilters(new URLSearchParams({
    resource: 'account_posts',
    product_code: productCode,
    country_code: getCountryReelFarmCode(country),
    account_id: accountId,
    limit: String(limit),
    offset: String(offset)
  }), dateFrom, dateTo);
  if (dataSource !== 'reelfarm') params.set('source', dataSource);
  return params;
}

export async function fetchAccountTagsAndIssues(accountIds: string[]) {
  const tagMap: Record<string, string[]> = {};
  const issueMap: Record<string, string[]> = {};
  for (let index = 0; index < accountIds.length; index += 80) {
    const batch = accountIds.slice(index, index + 80);
    const [tagPayload, issuePayload] = await Promise.all([
      api.accountTags(batch),
      api.accountIssues(batch)
    ]);
    Object.assign(tagMap, tagPayload.tags || {});
    Object.assign(issueMap, issuePayload.issues || {});
  }
  return { tagMap, issueMap };
}

export function attachAccountTagsAndIssues(accounts: AccountPoolAccount[], tagMap: Record<string, string[]>, issueMap: Record<string, string[]>) {
  return accounts.map(account => ({
    ...account,
    tags: tagMap[account.account_id] || [],
    issues: issueMap[account.account_id] || []
  }));
}

export function addTagToRows(rows: AccountPoolRow[], accountId: string, tag: string) {
  return rows.map(item => item.account_id === accountId
    ? { ...item, tags: Array.from(new Set([...(item.tags || []), tag])) }
    : item
  );
}

export function removeTagFromRows(rows: AccountPoolRow[], accountId: string, tag: string) {
  return rows.map(item => item.account_id === accountId
    ? { ...item, tags: (item.tags || []).filter(value => value !== tag) }
    : item
  );
}

export function removeProductTagFromRows(rows: AccountPoolRow[], deletedTag: string) {
  return rows.map(item => ({
    ...item,
    tags: (item.tags || []).filter(value => value.toLowerCase() !== deletedTag)
  }));
}

export function removeProductTagFromFilters(filters: TagFilterRow[], deletedTag: string) {
  return filters
    .map(filter => ({
      ...filter,
      tags: filter.tags.filter(value => value.toLowerCase() !== deletedTag)
    }))
    .filter(filter => filter.tags.length);
}
