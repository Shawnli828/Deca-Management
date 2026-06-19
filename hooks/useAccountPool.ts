'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  type AccountPoolRow,
  type ViewSortDirection,
  getAccountAvgViews,
  getAccountPoolPerformanceMetrics,
  getAccountRowKey,
  getPublishMethod
} from '@/components/AccountPoolHelpers';
import { ACCOUNT_POST_PAGE_SIZE, type AccountPostState } from '@/components/CountryAccountPosts';
import { type TagFilterRow } from '@/components/CountryAccountTags';
import { formatTagLabel, getTagCategory } from '@/components/ReelFarmAccountCard';
import { api } from '@/lib/api';
import { defaultDateRange } from '@/lib/dateRange';
import type { AccountSummary, Country, DetailedPostRow, Product } from '@/lib/types';
import { getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

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

  function addDateFilters(params: URLSearchParams) {
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    return params;
  }

  async function loadAccountPool() {
    setLoading(true);
    try {
      const productCode = getProductReelFarmCode(product);
      const productTagsRequest = api.productTags(productCode).catch(() => ({
        ok: false,
        product_code: productCode,
        tags: [] as string[]
      }));
      const accountsRequest = Promise.all(countries.map(async country => {
        const params = addDateFilters(new URLSearchParams({
          resource: 'accounts',
          product_code: productCode,
          country_code: getCountryReelFarmCode(country)
        }));
        if (dataSource !== 'reelfarm') params.set('source', dataSource);
        const payload = await api.dataQuery<{ ok: boolean; data: AccountSummary[] }>(params);
        return (payload.data || []).map(account => ({ ...account, country }));
      }));
      const [chunks, productTagsPayload] = await Promise.all([accountsRequest, productTagsRequest]);
      setProductTagOptions(productTagsPayload.tags || []);
      const accounts = chunks.flat();
      const accountIds = accounts.map(account => account.account_id).filter(Boolean);
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
      setRows(accounts.map(account => ({
        ...account,
        tags: tagMap[account.account_id] || [],
        issues: issueMap[account.account_id] || []
      })));
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
  }, [product.id, dataSource, dateFrom, dateTo]);

  useEffect(() => {
    setExpandedAccounts({});
    setPostCache({});
  }, [product.id, dataSource, dateFrom, dateTo]);

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
      const params = addDateFilters(new URLSearchParams({
        resource: 'account_posts',
        product_code: getProductReelFarmCode(product),
        country_code: getCountryReelFarmCode(row.country),
        account_id: row.account_id,
        limit: String(ACCOUNT_POST_PAGE_SIZE),
        offset: String(offset)
      }));
      if (dataSource !== 'reelfarm') params.set('source', dataSource);
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

  const tagOptions = useMemo(() => {
    return Array.from(new Set([
      ...productTagOptions,
      ...rows.flatMap(row => row.tags || [])
    ])).filter(Boolean).sort((a, b) => a.localeCompare(b));
  }, [productTagOptions, rows]);

  const editingTagRow = editingTagAccountId ? rows.find(row => row.account_id === editingTagAccountId) || null : null;

  async function addAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    const nextTag = tag.trim();
    if (!accountId || !nextTag) return;
    const productTagsPayload = await api.createProductTag(getProductReelFarmCode(product), nextTag);
    setProductTagOptions(productTagsPayload.tags || []);
    const payload = await api.addAccountTag(accountId, nextTag);
    setRows(previous => previous.map(item => item.account_id === accountId
      ? { ...item, tags: Array.from(new Set([...(item.tags || []), payload.tag])) }
      : item
    ));
  }

  async function removeAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    if (!accountId || !tag) return;
    await api.deleteAccountTag(accountId, tag);
    setRows(previous => previous.map(item => item.account_id === accountId
      ? { ...item, tags: (item.tags || []).filter(value => value !== tag) }
      : item
    ));
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
    setRows(previous => previous.map(item => ({
      ...item,
      tags: (item.tags || []).filter(value => value.toLowerCase() !== deletedTag)
    })));
    setTagFilters(previous => previous
      .map(filter => ({
        ...filter,
        tags: filter.tags.filter(value => value.toLowerCase() !== deletedTag)
      }))
      .filter(filter => filter.tags.length)
    );
  }

  const filteredRows = useMemo(() => {
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
  }, [countryFilter, dataSource, publishMethodFilter, rows, search, statusFilter, tagFilters]);

  const sortedRows = useMemo(() => {
    if (viewSort === 'none') return filteredRows;
    return [...filteredRows].sort((left, right) => {
      const leftViews = getAccountAvgViews(left);
      const rightViews = getAccountAvgViews(right);
      if (leftViews === rightViews) {
        return String(left.username || left.display_name || left.account_id || '')
          .localeCompare(String(right.username || right.display_name || right.account_id || ''));
      }
      return viewSort === 'desc' ? rightViews - leftViews : leftViews - rightViews;
    });
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
