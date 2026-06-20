'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  type AccountPoolRow,
  type ViewSortDirection,
  getAccountPoolPerformanceMetrics,
  getAccountRowKey,
  getAccountPoolTagOptions,
  filterAccountPoolRows,
  sortAccountPoolRows
} from '@/components/AccountPoolHelpers';
import { ACCOUNT_POST_PAGE_SIZE, type AccountPostState } from '@/components/CountryAccountPosts';
import { type TagFilterRow } from '@/components/CountryAccountTags';
import { api } from '@/lib/api';
import { defaultDateRange } from '@/lib/dateRange';
import { formatTagLabel } from '@/lib/tagUtils';
import type { AccountSummary, Country, DetailedPostRow, Product } from '@/lib/types';
import { getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';
import {
  addTagToRows,
  attachAccountTagsAndIssues,
  buildAccountPostsQueryParams,
  buildProductAccountPoolQueryParams,
  fetchAccountTagsAndIssues,
  removeProductTagFromFilters,
  removeProductTagFromRows,
  removeTagFromRows
} from './accountPoolStateHelpers';

export function useAccountPool({
  product,
  countries,
  dataSource,
  onSyncProduct
}: {
  product: Product;
  countries: Country[];
  dataSource: 'reelfarm' | 'museon_clone';
  onSyncProduct: (product: Product) => void | Promise<void>;
}) {
  const [rows, setRows] = useState<AccountPoolRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [countryFilter, setCountryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [publishMethodFilter, setPublishMethodFilter] = useState('all');
  const [tagFilters, setTagFilters] = useState<TagFilterRow[]>([]);
  const [dateFrom, setDateFrom] = useState(defaultDateRange.from);
  const [dateTo, setDateTo] = useState(defaultDateRange.to);
  const [viewSort, setViewSort] = useState<ViewSortDirection>('none');
  const [expandedAccounts, setExpandedAccounts] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, AccountPostState>>({});
  const [editingTagAccountId, setEditingTagAccountId] = useState('');
  const [productTagOptions, setProductTagOptions] = useState<string[]>([]);
  const countryKey = useMemo(
    () => countries.map(country => getCountryReelFarmCode(country)).join('|'),
    [countries]
  );

  async function loadAccountPool() {
    setLoading(true);
    setError('');
    try {
      const productCode = getProductReelFarmCode(product);
      const productTagsRequest = api.productTags(productCode).catch(() => ({
        ok: false,
        product_code: productCode,
        tags: [] as string[]
      }));
      const productTagsPayload = await productTagsRequest;
      if (!countries.length) {
        setProductTagOptions(productTagsPayload.tags || []);
        setRows([]);
        return;
      }

      const countryByCode = new Map(
        countries.map(country => [getCountryReelFarmCode(country).toUpperCase(), country])
      );
      const params = buildProductAccountPoolQueryParams({ productCode, dateFrom, dateTo, dataSource });
      const payload = await api.dataQuery<{ ok: boolean; data: AccountSummary[] }>(params);
      setProductTagOptions(productTagsPayload.tags || []);
      const accounts = (payload.data || [])
        .map(account => {
          const countryCode = String(account.country_code || account.market_code || '').toUpperCase();
          const country = countryByCode.get(countryCode) || (countries.length === 1 ? countries[0] : undefined);
          return country ? { ...account, country } : null;
        })
        .filter((account): account is AccountSummary & { country: Country } => Boolean(account));
      const accountIds = accounts.map(account => account.account_id).filter(Boolean);
      const { tagMap, issueMap } = await fetchAccountTagsAndIssues(accountIds);
      setRows(attachAccountTagsAndIssues(accounts, tagMap, issueMap));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown account pool loading error.';
      setRows([]);
      setError(`数据库账号池读取失败：${message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSyncProduct() {
    await onSyncProduct(product);
    await loadAccountPool();
  }

  useEffect(() => {
    loadAccountPool().catch(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product.id, dataSource, dateFrom, dateTo, countryKey]);

  useEffect(() => {
    setExpandedAccounts({});
    setPostCache({});
  }, [product.id, dataSource, dateFrom, dateTo, countryKey]);

  function accountRowKey(row: AccountPoolRow) {
    return getAccountRowKey(row, dateFrom, dateTo);
  }

  async function loadAccountPosts(row: AccountPoolRow, offset = 0) {
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
        productCode: getProductReelFarmCode(product),
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
    } catch (error: any) {
      setPostCache(previous => ({
        ...previous,
        [key]: {
          rows: previous[key]?.rows || [],
          offset,
          hasMore: false,
          total: previous[key]?.total,
          loading: false,
          error: error?.message || 'Posts loading failed.'
        }
      }));
    }
  }

  function toggleAccount(row: AccountPoolRow) {
    const key = accountRowKey(row);
    const isExpanded = Boolean(expandedAccounts[key]);
    setExpandedAccounts(previous => ({ ...previous, [key]: !isExpanded }));
    if (!isExpanded) {
      loadAccountPosts(row, postCache[key]?.offset || 0);
    }
  }

  const tagOptions = useMemo(
    () => getAccountPoolTagOptions(productTagOptions, rows),
    [productTagOptions, rows]
  );

  const editingTagRow = editingTagAccountId ? rows.find(row => row.account_id === editingTagAccountId) || null : null;

  async function addAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    const nextTag = tag.trim();
    if (!accountId || !nextTag) return;
    const productTagsPayload = await api.createProductTag(getProductReelFarmCode(product), nextTag);
    setProductTagOptions(productTagsPayload.tags || []);
    const payload = await api.addAccountTag(accountId, nextTag);
    setRows(previous => addTagToRows(previous, accountId, payload.tag));
  }

  async function removeAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    if (!accountId || !tag) return;
    await api.deleteAccountTag(accountId, tag);
    setRows(previous => removeTagFromRows(previous, accountId, tag));
  }

  async function deleteProductTagOption(tag: string) {
    const productCode = getProductReelFarmCode(product);
    const nextTag = tag.trim();
    if (!productCode || !nextTag) return;
    const confirmed = window.confirm(`删除 ${formatTagLabel(nextTag)} 吗？这个 Tag 会从当前产品所有账号上移除。`);
    if (!confirmed) return;
    const payload = await api.deleteProductTag(productCode, nextTag, true);
    const deletedTag = (payload.deleted_tag || nextTag).toLowerCase();
    setProductTagOptions(payload.tags || []);
    setRows(previous => removeProductTagFromRows(previous, deletedTag));
    setTagFilters(previous => removeProductTagFromFilters(previous, deletedTag));
  }

  const filteredRows = useMemo(() => filterAccountPoolRows({
    rows,
    search,
    countryFilter,
    statusFilter,
    publishMethodFilter,
    tagFilters,
    dataSource
  }), [countryFilter, dataSource, publishMethodFilter, rows, search, statusFilter, tagFilters]);

  const sortedRows = useMemo(() => {
    return sortAccountPoolRows(filteredRows, viewSort);
  }, [filteredRows, viewSort]);

  function toggleViewSort() {
    setViewSort(previous => previous === 'desc' ? 'asc' : 'desc');
  }

  const statusOptions = useMemo(() => {
    return Array.from(new Set(rows.map(row => String(row.status || 'unknown').toLowerCase()))).sort();
  }, [rows]);
  const performanceMetrics = useMemo(() => getAccountPoolPerformanceMetrics(filteredRows), [filteredRows]);

  return {
    rows,
    loading,
    error,
    search,
    setSearch,
    countryFilter,
    setCountryFilter,
    statusFilter,
    setStatusFilter,
    statusOptions,
    publishMethodFilter,
    setPublishMethodFilter,
    tagFilters,
    setTagFilters,
    tagOptions,
    dateFrom,
    dateTo,
    setDateFrom,
    setDateTo,
    viewSort,
    expandedAccounts,
    postCache,
    editingTagRow,
    setEditingTagAccountId,
    filteredRows,
    sortedRows,
    performanceMetrics,
    loadAccountPool,
    handleSyncProduct,
    accountRowKey,
    loadAccountPosts,
    toggleAccount,
    toggleViewSort,
    addAccountTag,
    removeAccountTag,
    deleteProductTagOption
  };
}
