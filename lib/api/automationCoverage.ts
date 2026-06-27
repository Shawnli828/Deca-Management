import type { AutomationCoveragePayload } from '../types';
import { apiFetch, jsonPostInit } from './client';

export type AutomationTargetInput = {
  productCode: string;
  countryCode: string;
  targetCount: number;
  note?: string;
};

export type AutomationWarmupInput = {
  productCode: string;
  countryCode: string;
  batchName?: string;
  accountCount: number;
  warmupStartDate: string;
  warmupDays: number;
  note?: string;
};

export const automationCoverageApi = {
  automationCoverage: () =>
    apiFetch<AutomationCoveragePayload>('/api/automation-coverage', undefined, 'Failed to load automation coverage'),
  saveAutomationCoverageTarget: (input: AutomationTargetInput) =>
    apiFetch<AutomationCoveragePayload>(
      '/api/automation-coverage/targets',
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_code: input.productCode,
          country_code: input.countryCode,
          target_count: input.targetCount,
          note: input.note || ''
        })
      },
      'Failed to save automation target'
    ),
  createAutomationWarmup: (input: AutomationWarmupInput) =>
    apiFetch<AutomationCoveragePayload>(
      '/api/automation-coverage/warmups',
      jsonPostInit({
        product_code: input.productCode,
        country_code: input.countryCode,
        batch_name: input.batchName || '',
        account_count: input.accountCount,
        warmup_start_date: input.warmupStartDate,
        warmup_days: input.warmupDays,
        note: input.note || ''
      }),
      'Failed to create automation warmup'
    )
};
