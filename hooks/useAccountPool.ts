'use client';

import { useEffect, useMemo } from 'react';
import type { AccountPoolDataSource } from '@/lib/domain/accountPool';
import type { Country, Product } from '@/lib/types';
import { getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';
import { useAccountPoolFilters } from './accountPool/useAccountPoolFilters';
import { useAccountPoolPosts } from './accountPool/useAccountPoolPosts';
import { useAccountPoolRows } from './accountPool/useAccountPoolRows';
import { useAccountPoolTags } from './accountPool/useAccountPoolTags';

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
  const productCode = useMemo(() => getProductReelFarmCode(product), [product]);
  const countryKey = useMemo(
    () => countries.map(country => getCountryReelFarmCode(country)).join('|'),
    [countries]
  );
  const {
    rows,
    setRows,
    loading,
    setLoading,
    error,
    dateFrom,
    dateTo,
    setDateFrom,
    setDateTo,
    productTagOptions,
    setProductTagOptions,
    loadAccountPool
  } = useAccountPoolRows({ productCode, countries, dataSource });

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

  const {
    editingTagRow,
    setEditingTagAccountId,
    addAccountTag,
    removeAccountTag,
    deleteProductTagOption
  } = useAccountPoolTags({
    productCode,
    rows,
    setRows,
    setProductTagOptions,
    setTagFilters
  });

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
