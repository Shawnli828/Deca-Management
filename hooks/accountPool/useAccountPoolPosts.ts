import { useCallback, useState } from 'react';
import { ACCOUNT_POST_PAGE_SIZE, type AccountPostState } from '@/components/CountryAccountPosts';
import { api, getErrorMessage } from '@/lib/api';
import {
  type AccountPoolDataSource,
  type AccountPoolRow,
  getAccountRowKey
} from '@/lib/domain/accountPool';
import type { DetailedPostRow } from '@/lib/types';
import {
  buildAccountPostsQueryParams
} from '../accountPoolStateHelpers';

type UseAccountPoolPostsOptions = {
  productCode: string;
  dateFrom: string;
  dateTo: string;
  dataSource: AccountPoolDataSource;
};

export function useAccountPoolPosts({ productCode, dateFrom, dateTo, dataSource }: UseAccountPoolPostsOptions) {
  const [expandedAccounts, setExpandedAccounts] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, AccountPostState>>({});

  const accountRowKey = useCallback((row: AccountPoolRow) => {
    return getAccountRowKey(row, dateFrom, dateTo);
  }, [dateFrom, dateTo]);

  const loadAccountPosts = useCallback(async (row: AccountPoolRow, offset = 0) => {
    const key = accountRowKey(row);
    const cached = postCache[key];
    if (cached && cached.offset === offset && cached.rows.length && !cached.error) return;

    setPostCache(previous => ({
      ...previous,
      [key]: {
        rows: previous[key]?.rows || [],
        offset,
        hasMore: previous[key]?.hasMore || false,
        total: previous[key]?.total,
        loading: true,
        error: ''
      }
    }));

    try {
      const params = buildAccountPostsQueryParams({
        productCode,
        country: row.country,
        accountId: row.account_id,
        limit: ACCOUNT_POST_PAGE_SIZE,
        offset,
        dateFrom,
        dateTo,
        dataSource
      });
      const payload = await api.dataQuery<{
        ok: boolean;
        data: DetailedPostRow[];
        pagination?: { limit: number; offset: number; has_more: boolean; total?: number };
      }>(params);
      setPostCache(previous => ({
        ...previous,
        [key]: {
          rows: payload.data || [],
          offset,
          hasMore: Boolean(payload.pagination?.has_more),
          total: payload.pagination?.total,
          loading: false,
          error: ''
        }
      }));
    } catch (error: unknown) {
      setPostCache(previous => ({
        ...previous,
        [key]: {
          rows: previous[key]?.rows || [],
          offset,
          hasMore: false,
          total: previous[key]?.total,
          loading: false,
          error: getErrorMessage(error, 'Posts loading failed.')
        }
      }));
    }
  }, [accountRowKey, dataSource, dateFrom, dateTo, postCache, productCode]);

  const toggleAccount = useCallback((row: AccountPoolRow) => {
    const key = accountRowKey(row);
    const isExpanded = Boolean(expandedAccounts[key]);
    setExpandedAccounts(previous => ({ ...previous, [key]: !isExpanded }));
    if (!isExpanded) {
      loadAccountPosts(row, postCache[key]?.offset || 0);
    }
  }, [accountRowKey, expandedAccounts, loadAccountPosts, postCache]);

  const resetAccountPosts = useCallback(() => {
    setExpandedAccounts({});
    setPostCache({});
  }, []);

  return {
    expandedAccounts,
    postCache,
    accountRowKey,
    loadAccountPosts,
    toggleAccount,
    resetAccountPosts
  };
}
