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

export function useFeishuReport() {
  const [reportDate, setReportDate] = useState(localIsoDate(-1));
  const [payload, setPayload] = useState<DailyFeishuPreviewPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [sendResult, setSendResult] = useState<DailyFeishuSendResult | null>(null);
  const [sendMode, setSendMode] = useState<FeishuSendMode>('card_with_text_fallback');
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
    error,
    sendResult,
    sendMode,
    setSendMode,
    totals,
    products,
    downloadRate,
    loadPreview,
    sendReport
  };
}
