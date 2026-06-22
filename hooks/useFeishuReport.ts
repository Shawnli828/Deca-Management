'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import {
  localIsoDate,
  ratio,
  reportTotals
} from '@/lib/feishuReportHelpers';
import type {
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  FeishuSendMode
} from '@/lib/types';

const MIXPANEL_SYNC_PRODUCT_CODES = ['DB', 'DM', 'DL'] as const;
const MIXPANEL_SYNC_DAYS = 30;

export type FeishuGrowthSyncResult = {
  ok: boolean;
  syncedAt: string;
  products: Array<{
    productCode: string;
    count: number;
  }>;
  errors: Array<{
    productCode: string;
    message: string;
  }>;
};

export function useFeishuReport() {
  const [reportDate, setReportDate] = useState(localIsoDate(-1));
  const [payload, setPayload] = useState<DailyFeishuPreviewPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [syncingGrowth, setSyncingGrowth] = useState(false);
  const [error, setError] = useState('');
  const [sendResult, setSendResult] = useState<DailyFeishuSendResult | null>(null);
  const [growthSyncResult, setGrowthSyncResult] = useState<FeishuGrowthSyncResult | null>(null);
  const [sendMode, setSendMode] = useState<FeishuSendMode>('image');
  const previewRequestRef = useRef(0);

  const totals = useMemo(() => reportTotals(payload?.report), [payload]);
  const products = payload?.report?.products || [];
  const downloadRate = ratio(totals.download_rate);

  const loadPreview = useCallback(async (nextDate = reportDate, nextMode = sendMode) => {
    const requestId = previewRequestRef.current + 1;
    previewRequestRef.current = requestId;
    setLoading(true);
    setError('');
    setSendResult(null);
    try {
      const next = await api.dailyFeishuPreview(nextDate, nextMode);
      if (previewRequestRef.current !== requestId) return;
      setPayload(next);
    } catch (previewError: unknown) {
      if (previewRequestRef.current !== requestId) return;
      setError(getErrorMessage(previewError, '日报预览读取失败'));
    } finally {
      if (previewRequestRef.current === requestId) setLoading(false);
    }
  }, [reportDate, sendMode]);

  const sendReport = useCallback(async () => {
    setSending(true);
    setError('');
    setSendResult(null);
    setGrowthSyncResult(null);
    try {
      const result = await api.sendDailyFeishuReport(reportDate, { mode: sendMode });
      setSendResult(result);
      await loadPreview(reportDate, sendMode);
    } catch (sendError: unknown) {
      setError(getErrorMessage(sendError, '飞书发送失败'));
    } finally {
      setSending(false);
    }
  }, [loadPreview, reportDate, sendMode]);

  const syncMixpanelGrowth = useCallback(async () => {
    setSyncingGrowth(true);
    setError('');
    setSendResult(null);
    setGrowthSyncResult(null);
    try {
      const result = await api.syncProductsGrowth(MIXPANEL_SYNC_PRODUCT_CODES, MIXPANEL_SYNC_DAYS);
      const products = (result.records || []).map(item => ({
        productCode: item.product_code || '',
        count: item.count || 0
      })).filter(item => item.productCode);
      const errors = (result.errors || []).map(item => ({
        productCode: item.product_code || '',
        message: item.error || item.message || 'Mixpanel 同步失败'
      }));

      if (products.length) {
        await loadPreview(reportDate, sendMode);
      }
      setGrowthSyncResult({
        ok: Boolean(result.ok) && errors.length === 0,
        syncedAt: result.finished_at || new Date().toISOString(),
        products,
        errors
      });
      if (errors.length) {
        setError(`Mixpanel 同步未全部完成：${errors.map(item => `${item.productCode} ${item.message}`).join('；')}`);
      }
    } finally {
      setSyncingGrowth(false);
    }
  }, [loadPreview, reportDate, sendMode]);

  useEffect(() => {
    void loadPreview(reportDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    reportDate,
    setReportDate,
    payload,
    loading,
    sending,
    syncingGrowth,
    error,
    sendResult,
    growthSyncResult,
    sendMode,
    setSendMode,
    totals,
    products,
    downloadRate,
    loadPreview,
    sendReport,
    syncMixpanelGrowth
  };
}
