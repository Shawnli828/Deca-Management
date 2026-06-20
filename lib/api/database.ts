import type { DatabaseSnapshot, ExternalApiKey } from '../types';
import { apiFetch, jsonPostInit } from './client';

export const databaseApi = {
  database: () => apiFetch<DatabaseSnapshot>('/api/database', undefined, 'Failed to load database'),
  apiKeys: () => apiFetch<{ ok: boolean; keys: ExternalApiKey[] }>('/api/api-keys'),
  createApiKey: (name: string) =>
    apiFetch<{ ok: boolean; key: string; record: ExternalApiKey }>('/api/api-keys', jsonPostInit({ name })),
  revokeApiKey: (id: string) =>
    apiFetch<{ ok: boolean; record: ExternalApiKey }>('/api/api-keys/revoke', jsonPostInit({ id }))
};
