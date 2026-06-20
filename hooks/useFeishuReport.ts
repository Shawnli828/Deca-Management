'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import {
  DEFAULT_LLM_MODEL,
  FALLBACK_MODEL_OPTIONS,
  localIsoDate,
  ratio,
  reportTotals
} from '@/lib/feishuReportHelpers';
import type {
  DailyFeishuAnalysisPayload,
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
  const [model, setModel] = useState(DEFAULT_LLM_MODEL);
  const [modelOptions, setModelOptions] = useState(FALLBACK_MODEL_OPTIONS);
  const [modelListStatus, setModelListStatus] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [includeAi, setIncludeAi] = useState(false);
  const [sendMode, setSendMode] = useState<FeishuSendMode>('card_with_text_fallback');
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisPayload, setAnalysisPayload] = useState<DailyFeishuAnalysisPayload | null>(null);
  const [analysisError, setAnalysisError] = useState('');
  const previewRequestRef = useRef(0);
  const analysisRequestRef = useRef(0);

  const totals = useMemo(() => reportTotals(payload?.report), [payload]);
  const products = payload?.report?.products || [];
  const downloadRate = ratio(totals.download_rate);
  const selectedModel = customModel.trim() || model;

  const loadPreview = useCallback(async (nextDate = reportDate, nextMode = sendMode) => {
    const requestId = previewRequestRef.current + 1;
    previewRequestRef.current = requestId;
    setLoading(true);
    setError('');
    setSendResult(null);
    setAnalysisPayload(null);
    setAnalysisError('');
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
      const result = await api.sendDailyFeishuReport(reportDate, { includeAi, model: selectedModel, mode: sendMode });
      setSendResult(result);
      await loadPreview(reportDate, sendMode);
    } catch (sendError: unknown) {
      setError(getErrorMessage(sendError, '飞书发送失败'));
    } finally {
      setSending(false);
    }
  }, [includeAi, loadPreview, reportDate, selectedModel, sendMode]);

  const generateAnalysis = useCallback(async () => {
    const requestId = analysisRequestRef.current + 1;
    analysisRequestRef.current = requestId;
    setAnalysisLoading(true);
    setAnalysisError('');
    setAnalysisPayload(null);
    try {
      const result = await api.dailyFeishuAnalysis(reportDate, selectedModel);
      if (analysisRequestRef.current !== requestId) return;
      setAnalysisPayload(result);
    } catch (analysisException: unknown) {
      if (analysisRequestRef.current !== requestId) return;
      setAnalysisError(getErrorMessage(analysisException, 'AI 分析生成失败'));
    } finally {
      if (analysisRequestRef.current === requestId) setAnalysisLoading(false);
    }
  }, [reportDate, selectedModel]);

  useEffect(() => {
    void loadPreview(reportDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.llmModels()
      .then(result => {
        if (cancelled) return;
        const options = (Array.isArray(result.models) && result.models.length > 0)
          ? result.models
          : FALLBACK_MODEL_OPTIONS;
        setModelOptions(options);
        setModel(current => {
          if (options.includes(current)) return current;
          if (result.default_model && options.includes(result.default_model)) return result.default_model;
          return options[0] || DEFAULT_LLM_MODEL;
        });
        if (result.fallback && result.error) {
          setModelListStatus(`模型列表使用默认候选：${result.error}`);
        } else if (result.fallback || result.needs_api_key) {
          setModelListStatus('模型列表使用默认候选。');
        } else {
          setModelListStatus(`${options.length} 个可用 GPT 模型`);
        }
      })
      .catch((modelError: unknown) => {
        if (cancelled) return;
        setModelOptions(FALLBACK_MODEL_OPTIONS);
        setModelListStatus(getErrorMessage(modelError, '模型列表读取失败，使用默认候选。'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (sendMode === 'card' && includeAi) {
      setIncludeAi(false);
    }
  }, [includeAi, sendMode]);

  return {
    reportDate,
    setReportDate,
    payload,
    loading,
    sending,
    error,
    sendResult,
    model,
    setModel,
    modelOptions,
    modelListStatus,
    customModel,
    setCustomModel,
    includeAi,
    setIncludeAi,
    sendMode,
    setSendMode,
    analysisLoading,
    analysisPayload,
    analysisError,
    totals,
    products,
    downloadRate,
    selectedModel,
    loadPreview,
    sendReport,
    generateAnalysis
  };
}
