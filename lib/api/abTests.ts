import type { ABTestDetailPayload, ABTestRecord, ABTestsPayload } from '../types';
import { apiFetch, jsonPostInit } from './client';

export type ABTestInput = {
  name?: string;
  product_code?: string;
  country_code?: string;
  start_date?: string;
  duration_days?: number;
  control_start_date?: string;
  control_end_date?: string;
  test_start_date?: string;
  test_end_date?: string;
  variable?: string;
  hypothesis?: string;
  note?: string;
  conclusion?: string;
  conclusion_status?: string;
};

export const abTestsApi = {
  abTests: () =>
    apiFetch<ABTestsPayload>('/api/ab-tests', undefined, 'Failed to load AB tests'),
  abTest: (id: string) =>
    apiFetch<ABTestDetailPayload>(`/api/ab-tests/${encodeURIComponent(id)}`, undefined, 'Failed to load AB test'),
  createAbTest: (payload: ABTestInput) =>
    apiFetch<ABTestDetailPayload>('/api/ab-tests', jsonPostInit(payload), 'Failed to create AB test'),
  updateAbTest: (id: string, payload: ABTestInput) =>
    apiFetch<ABTestDetailPayload>(
      `/api/ab-tests/${encodeURIComponent(id)}`,
      { ...jsonPostInit(payload), method: 'PATCH' },
      'Failed to update AB test'
    ),
  deleteAbTest: (id: string) =>
    apiFetch<{ ok: boolean; deleted: Pick<ABTestRecord, 'id'> }>(
      `/api/ab-tests/${encodeURIComponent(id)}`,
      { method: 'DELETE' },
      'Failed to delete AB test'
    )
};
