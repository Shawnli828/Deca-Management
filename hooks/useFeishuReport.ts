'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
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
  DailyFeishuSendResult
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
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisPayload, setAnalysisPayload] = useState<DailyFeishuAnalysisPayload | null>(null);
  const [analysisError, setAnalysisError] = useState('');

  const totals = useMemo(() => reportTotals(payload?.report), [payload]);
  const products = payload?.report?.products || [];
  const downloadRate = ratio(totals.download_rate);
  const selectedModel = customModel.trim() || model;

  const loadPreview = useCallback(async (nextDate = reportDate) => {
    setLoading(true);
    setError('');
    setSendResult(null);
    setAnalysisPayload(null);
    setAnalysisError('');
    try {
      const next = await api.dailyFeishuPreview(nextDate);
      setPayload(next);
    } catch (previewError: any) {
      setError(previewError?.message || '日报预览读取失败');
    } finally {
      setLoading(false);
    }
  }, [reportDate]);

  const sendReport = useCallback(async () => {
    setSending(true);
    setError('');
    setSendResult(null);
    try {
      const result = await api.sendDailyFeishuReport(reportDate, { includeAi, model: selectedModel });
      setSendResult(result);
      await loadPreview(reportDate);
    } catch (sendError: any) {
      setError(sendError?.message || '飞书发送失败');
    } finally {
      setSending(false);
    }
  }, [includeAi, loadPreview, reportDate, selectedModel]);

  const generateAnalysis = useCallback(async () => {
    setAnalysisLoading(true);
    setAnalysisError('');
    setAnalysisPayload(null);
    try {
      const result = await api.dailyFeishuAnalysis(reportDate, selectedModel);
      setAnalysisPayload(result);
    } catch (analysisException: any) {
      setAnalysisError(analysisException?.message || 'AI 分析生成失败');
    } finally {
      setAnalysisLoading(false);
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
      .catch(modelError => {
        if (cancelled) return;
        setModelOptions(FALLBACK_MODEL_OPTIONS);
        setModelListStatus(modelError?.message || '模型列表读取失败，使用默认候选。');
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
