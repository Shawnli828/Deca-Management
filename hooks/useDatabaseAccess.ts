import { useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import type { DatabaseSnapshot, ExternalApiKey } from '@/lib/types';

type UseDatabaseAccessOptions = {
  onStatus: (message: string, isError?: boolean) => void;
};

export function useDatabaseAccess({ onStatus }: UseDatabaseAccessOptions) {
  const [databaseOpen, setDatabaseOpen] = useState(false);
  const [snapshot, setSnapshot] = useState<DatabaseSnapshot | null>(null);
  const [apiKeys, setApiKeys] = useState<ExternalApiKey[]>([]);
  const [generatedKey, setGeneratedKey] = useState('');

  async function loadApiKeys() {
    try {
      const payload = await api.apiKeys();
      setApiKeys(payload.keys || []);
      return payload.keys || [];
    } catch (error: unknown) {
      onStatus(getErrorMessage(error, 'API Key 读取失败'), true);
      throw error;
    }
  }

  async function openDatabase() {
    setDatabaseOpen(true);
    setGeneratedKey('');
    await loadApiKeys();
  }

  async function refreshDatabase() {
    setSnapshot(await api.database());
  }

  async function createKey(name: string) {
    const payload = await api.createApiKey(name);
    setGeneratedKey(payload.key);
    await loadApiKeys();
  }

  async function revokeKey(id: string) {
    if (!confirm('确定要停用这个 API Key 吗？停用后外部 AI 将无法继续使用它。')) return;
    await api.revokeApiKey(id);
    await loadApiKeys();
  }

  async function copy(value: string) {
    await navigator.clipboard.writeText(value);
    onStatus('已复制');
  }

  return {
    databaseOpen,
    snapshot,
    apiKeys,
    generatedKey,
    setDatabaseOpen,
    loadApiKeys,
    openDatabase,
    refreshDatabase,
    createKey,
    revokeKey,
    copy
  };
}
