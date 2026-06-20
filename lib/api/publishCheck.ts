import type { PublishCheckResult, PublishCheckState } from '../types';
import { apiFetch, jsonPostInit } from './client';

export const publishCheckApi = {
  publishCheck: () => apiFetch<{ ok: boolean; state: PublishCheckState }>('/api/publish-check', undefined, 'Failed to load publish check'),
  savePublishCheck: (state: PublishCheckState) =>
    apiFetch<{ ok: boolean; state: PublishCheckState }>('/api/publish-check', jsonPostInit({ state }), 'Failed to save publish check'),
  runPublishCheck: () => apiFetch<PublishCheckResult>('/api/publish-check/run', { method: 'POST' }, 'Failed to run publish check'),
  sendPublishCheckReminder: () =>
    apiFetch<{ ok: boolean; sent_at?: string; missing_accounts?: number; message_preview?: string }>(
      '/api/publish-check/send-reminder',
      { method: 'POST' },
      'Failed to send Feishu reminder'
    )
};
