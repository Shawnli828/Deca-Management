'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import type { AutomationCoveragePayload } from '@/lib/types';

type TargetInput = {
  productCode: string;
  countryCode: string;
  targetCount: number;
  note?: string;
};

type WarmupInput = {
  productCode: string;
  countryCode: string;
  batchName?: string;
  accountCount: number;
  warmupStartDate: string;
  warmupDays: number;
  note?: string;
};

export function useAutomationCoverage({ enabled = true }: { enabled?: boolean } = {}) {
  const [payload, setPayload] = useState<AutomationCoveragePayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadCoverage = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPayload(await api.automationCoverage());
    } catch (err) {
      setError(getErrorMessage(err, '加载自动化覆盖失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const saveTarget = useCallback(async (input: TargetInput) => {
    setSaving(true);
    setError('');
    try {
      setPayload(await api.saveAutomationCoverageTarget(input));
    } catch (err) {
      setError(getErrorMessage(err, '保存目标失败'));
      throw err;
    } finally {
      setSaving(false);
    }
  }, []);

  const createWarmup = useCallback(async (input: WarmupInput) => {
    setSaving(true);
    setError('');
    try {
      setPayload(await api.createAutomationWarmup(input));
    } catch (err) {
      setError(getErrorMessage(err, '登记养号失败'));
      throw err;
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      void loadCoverage();
    }
  }, [enabled, loadCoverage]);

  return {
    payload,
    loading,
    saving,
    error,
    loadCoverage,
    saveTarget,
    createWarmup
  };
}
