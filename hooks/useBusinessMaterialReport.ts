'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import type { BusinessMaterialReportPayload, Product } from '@/lib/types';
import { getProductReelFarmCode } from '@/lib/utils';

type UseBusinessMaterialReportOptions = {
  products: Product[];
  mode?: string;
  errorMessage: string;
};

export function businessIsoDate(offset = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

export function useBusinessMaterialReport({
  products,
  mode,
  errorMessage
}: UseBusinessMaterialReportOptions) {
  const [productId, setProductId] = useState('');
  const [days, setDays] = useState(7);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [payload, setPayload] = useState<BusinessMaterialReportPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const reportRequestRef = useRef(0);

  const selectedProduct = useMemo(
    () => products.find(product => product.id === productId) || products[0] || null,
    [products, productId]
  );
  const productCode = selectedProduct ? getProductReelFarmCode(selectedProduct) : '';
  const customRange = Boolean(dateFrom || dateTo);

  async function loadReport() {
    if (!productCode) return;
    const requestId = reportRequestRef.current + 1;
    reportRequestRef.current = requestId;
    setLoading(true);
    setError('');
    try {
      const next = await api.businessMaterialReport(productCode, {
        days,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        ...(mode ? { mode } : {})
      });
      if (reportRequestRef.current !== requestId) return;
      setPayload(next);
    } catch (loadError: unknown) {
      if (reportRequestRef.current !== requestId) return;
      setError(getErrorMessage(loadError, errorMessage));
    } finally {
      if (reportRequestRef.current === requestId) setLoading(false);
    }
  }

  useEffect(() => {
    if (!productId && products[0]) setProductId(products[0].id);
  }, [products, productId]);

  useEffect(() => {
    void loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productCode, days]);

  return {
    productId,
    setProductId,
    days,
    setDays,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    payload,
    loading,
    error,
    selectedProduct,
    productCode,
    customRange,
    loadReport
  };
}
