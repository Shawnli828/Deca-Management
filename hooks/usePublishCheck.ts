import { useState } from 'react';
import { api } from '@/lib/api';
import type { PublishCheckState } from '@/lib/types';

type UsePublishCheckOptions = {
  onStatus: (message: string, isError?: boolean) => void;
};

const emptyPublishCheck: PublishCheckState = { assignments: [], last_result: null };

export function usePublishCheck({ onStatus }: UsePublishCheckOptions) {
  const [publishCheck, setPublishCheck] = useState<PublishCheckState>(emptyPublishCheck);
  const [publishCheckRunning, setPublishCheckRunning] = useState(false);
  const [publishReminderSending, setPublishReminderSending] = useState(false);

  async function loadPublishCheck() {
    try {
      const payload = await api.publishCheck();
      setPublishCheck(payload.state || emptyPublishCheck);
    } catch {
      setPublishCheck(emptyPublishCheck);
    }
  }

  async function savePublishCheck(next: PublishCheckState) {
    setPublishCheck(next);
    try {
      const payload = await api.savePublishCheck(next);
      setPublishCheck(payload.state);
      onStatus('发布检查配置已保存');
    } catch {
      onStatus('发布检查配置保存失败', true);
    }
  }

  async function runPublishCheckNow() {
    setPublishCheckRunning(true);
    try {
      const result = await api.runPublishCheck();
      setPublishCheck(prev => ({ ...prev, last_result: result }));
      onStatus(`发布检查完成：${result.totals?.missing_accounts || 0} 个账号未发布`);
    } catch (error: any) {
      onStatus(error?.message || '发布检查失败', true);
    } finally {
      setPublishCheckRunning(false);
    }
  }

  async function sendPublishReminderNow() {
    setPublishReminderSending(true);
    try {
      const result = await api.sendPublishCheckReminder();
      onStatus(`飞书提醒已发送：${result.missing_accounts || 0} 个账号未发布`);
    } catch (error: any) {
      onStatus(error?.message || '飞书提醒发送失败', true);
    } finally {
      setPublishReminderSending(false);
    }
  }

  return {
    publishCheck,
    publishCheckRunning,
    publishReminderSending,
    loadPublishCheck,
    savePublishCheck,
    runPublishCheckNow,
    sendPublishReminderNow
  };
}
