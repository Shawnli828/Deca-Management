'use client';

import { useCallback, useState } from 'react';
import { defaultDateRange } from '@/lib/dateRange';
import type { AccountPoolDataSource, AccountPoolRow } from '@/lib/domain/accountPool';
import type { Country } from '@/lib/types';
import { loadAccountPoolRows } from './accountPoolData';

type UseAccountPoolRowsOptions = {
  productCode: string;
  countries: Country[];
  dataSource: AccountPoolDataSource;
};

export function useAccountPoolRows({ productCode, countries, dataSource }: UseAccountPoolRowsOptions) {
  const [rows, setRows] = useState<AccountPoolRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState(defaultDateRange.from);
  const [dateTo, setDateTo] = useState(defaultDateRange.to);
  const [productTagOptions, setProductTagOptions] = useState<string[]>([]);

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

  return {
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
  };
}
