'use client';

import { localIsoDate } from '@/lib/feishuReportHelpers';
import type { FeishuSendMode } from '@/lib/types';

type FeishuReportHeroProps = {
  reportDate: string;
  setReportDate: (value: string) => void;
  loading: boolean;
  sending: boolean;
  syncingGrowth: boolean;
  syncingSources: boolean;
  sendMode: FeishuSendMode;
  setSendMode: (value: FeishuSendMode) => void;
  loadPreview: (date: string) => void;
  sendReport: () => void;
  syncMixpanelGrowth: () => void;
  syncReelfarmAndMuseon: () => void;
};

export function FeishuReportHero({
  reportDate,
  setReportDate,
  loading,
  sending,
  syncingGrowth,
  syncingSources,
  sendMode,
  setSendMode,
  loadPreview,
  sendReport,
  syncMixpanelGrowth,
  syncReelfarmAndMuseon
}: FeishuReportHeroProps) {
  return (
    <header className="feishu-report-hero">
      <div>
        <p className="dashboard-kicker">Feishu Report</p>
        <h1>Feishu Report</h1>
        <p>每日业务数据先生成可检查预览，再发送为飞书图片看板。</p>
      </div>
      <div className="feishu-report-actions">
        <label>
          <span>业务日</span>
          <input type="date" value={reportDate} max={localIsoDate()} onChange={event => setReportDate(event.target.value)} />
        </label>
        <label>
          <span>发送模式</span>
          <select value={sendMode} onChange={event => setSendMode(event.target.value as FeishuSendMode)}>
            <option value="image">SVG 图片看板</option>
            <option value="card_with_text_fallback">Webhook 卡片优先</option>
            <option value="card">仅 Webhook 卡片</option>
            <option value="template">模板卡片</option>
          </select>
        </label>
        <button type="button" onClick={() => loadPreview(reportDate)} disabled={loading}>
          {loading ? '生成中...' : '生成预览'}
        </button>
        <button type="button" onClick={syncReelfarmAndMuseon} disabled={syncingSources || syncingGrowth || loading || sending}>
          {syncingSources ? '同步中...' : '同步 RF + Museon'}
        </button>
        <button type="button" onClick={syncMixpanelGrowth} disabled={syncingGrowth || syncingSources || loading || sending}>
          {syncingGrowth ? '同步中...' : '同步 Mixpanel'}
        </button>
        <button className="primary" type="button" onClick={sendReport} disabled={sending || syncingSources || syncingGrowth || loading}>
          {sending ? '发送中...' : '发送飞书'}
        </button>
      </div>
    </header>
  );
}
