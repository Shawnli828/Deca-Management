'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import { defaultDateRange } from '@/lib/dateRange';
import type { AccountPoolDataSource, AccountPoolRow } from '@/lib/domain/accountPool';
import { formatTagLabel } from '@/lib/tagUtils';
import type { Country, Product } from '@/lib/types';
import { getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';
import {
  addTagToRows,
  removeProductTagFromFilters,
  removeProductTagFromRows,
  removeTagFromRows
} from './accountPoolStateHelpers';
import { loadAccountPoolRows } from './accountPool/accountPoolData';
import { useAccountPoolFilters } from './accountPool/useAccountPoolFilters';
import { useAccountPoolPosts } from './accountPool/useAccountPoolPosts';

export function useAccountPool({
  product,
  countries,
  dataSource,
  onSyncProduct
}: {
  product: Product;
  countries: Country[];
  dataSource: AccountPoolDataSource;
  onSyncProduct: (product: Product) => void | Promise<void>;
}) {
  const [rows, setRows] = useState<AccountPoolRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState(defaultDateRange.from);
  const [dateTo, setDateTo] = useState(defaultDateRange.to);
  const [editingTagAccountId, setEditingTagAccountId] = useState('');
  const [productTagOptions, setProductTagOptions] = useState<string[]>([]);
  const productCode = useMemo(() => getProductReelFarmCode(product), [product]);
  const countryKey = useMemo(
    () => countries.map(country => getCountryReelFarmCode(country)).join('|'),
    [countries]
  );

  const {
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
    viewSort,
    filteredRows,
    sortedRows,
    performanceMetrics,
    toggleViewSort
  } = useAccountPoolFilters({ rows, productTagOptions, dataSource });

  const {
    expandedAccounts,
    postCache,
    accountRowKey,
    loadAccountPosts,
    toggleAccount,
    resetAccountPosts
  } = useAccountPoolPosts({ productCode, dateFrom, dateTo, dataSource });

  const loadAccountPool = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await loadAccountPoolRows({
        productCode,
        countries,
        dateFrom,
        dateTo,
        dataSource
      });
      setProductTagOptions(payload.productTags);
      setRows(payload.rows);
      if (payload.failures.length) {
        setError(`部分国家账号读取失败：${payload.failures.join('; ')}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown account pool loading error.';
      setRows([]);
      setError(`数据库账号池读取失败：${message}`);
    } finally {
      setLoading(false);
    }
  }, [countries, dataSource, dateFrom, dateTo, productCode]);

  async function handleSyncProduct() {
    await onSyncProduct(product);
    await loadAccountPool();
  }

  useEffect(() => {
    loadAccountPool().catch(() => setLoading(false));
  }, [loadAccountPool]);

  useEffect(() => {
    resetAccountPosts();
  }, [product.id, dataSource, dateFrom, dateTo, countryKey, resetAccountPosts]);

  const editingTagRow = editingTagAccountId ? rows.find(row => row.account_id === editingTagAccountId) || null : null;

  async function addAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    const nextTag = tag.trim();
    if (!accountId || !nextTag) return;
    const productTagsPayload = await api.createProductTag(productCode, nextTag);
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
