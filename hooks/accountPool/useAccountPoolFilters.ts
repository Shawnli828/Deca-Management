import { useDeferredValue, useMemo, useState } from 'react';
import {
  type AccountPoolDataSource,
  type AccountPoolRow,
  type ViewSortDirection,
  filterAccountPoolRows,
  getAccountPoolPerformanceMetrics,
  getAccountPoolTagOptions,
  sortAccountPoolRows
} from '@/lib/domain/accountPool';
import type { TagFilterRow } from '@/lib/domain/accountTags';

type UseAccountPoolFiltersOptions = {
  rows: AccountPoolRow[];
  productTagOptions: string[];
  dataSource: AccountPoolDataSource;
};

export function useAccountPoolFilters({ rows, productTagOptions, dataSource }: UseAccountPoolFiltersOptions) {
  const [search, setSearch] = useState('');
  const [countryFilter, setCountryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [publishMethodFilter, setPublishMethodFilter] = useState('all');
  const [tagFilters, setTagFilters] = useState<TagFilterRow[]>([]);
  const [viewSort, setViewSort] = useState<ViewSortDirection>('none');
  const deferredSearch = useDeferredValue(search);

  const tagOptions = useMemo(
    () => getAccountPoolTagOptions(productTagOptions, rows),
    [productTagOptions, rows]
  );
  const filteredRows = useMemo(() => filterAccountPoolRows({
    rows,
    search: deferredSearch,
    countryFilter,
    statusFilter,
    publishMethodFilter,
    tagFilters,
    dataSource
  }), [countryFilter, dataSource, deferredSearch, publishMethodFilter, rows, statusFilter, tagFilters]);
  const sortedRows = useMemo(() => sortAccountPoolRows(filteredRows, viewSort), [filteredRows, viewSort]);
  const statusOptions = useMemo(() => {
    return Array.from(new Set(rows.map(row => String(row.status || 'unknown').toLowerCase()))).sort();
  }, [rows]);
  const performanceMetrics = useMemo(() => getAccountPoolPerformanceMetrics(filteredRows), [filteredRows]);

  function toggleViewSort() {
    setViewSort(previous => previous === 'desc' ? 'asc' : 'desc');
  }

  return {
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
  };
}
