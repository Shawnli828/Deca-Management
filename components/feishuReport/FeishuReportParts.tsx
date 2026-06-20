'use client';

import { localIsoDate } from '@/lib/feishuReportHelpers';
import type { DailyFeishuAnalysisPayload, FeishuSendMode } from '@/lib/types';

type FeishuReportHeroProps = {
  reportDate: string;
  setReportDate: (value: string) => void;
  loading: boolean;
  sending: boolean;
  sendMode: FeishuSendMode;
  setSendMode: (value: FeishuSendMode) => void;
  loadPreview: (date: string) => void;
  sendReport: () => void;
};

export function FeishuReportHero({
  reportDate,
  setReportDate,
  loading,
  sending,
  sendMode,
  setSendMode,
  loadPreview,
  sendReport
}: FeishuReportHeroProps) {
  return (
    <header className="feishu-report-hero">
      <div>
        <p className="dashboard-kicker">AI Feishu Report</p>
        <h1>Feishu Report</h1>
        <p>每日业务数据先生成可检查预览，再以飞书原生交互卡片发送到群里；文本日报保留为兜底模式。</p>
      </div>
      <div className="feishu-report-actions">
        <label>
          <span>业务日</span>
          <input type="date" value={reportDate} max={localIsoDate()} onChange={event => setReportDate(event.target.value)} />
        </label>
        <label>
          <span>发送模式</span>
          <select value={sendMode} onChange={event => setSendMode(event.target.value as FeishuSendMode)}>
            <option value="card_with_text_fallback">卡片优先</option>
            <option value="card">仅卡片</option>
            <option value="text">仅文本</option>
          </select>
        </label>
        <button type="button" onClick={() => loadPreview(reportDate)} disabled={loading}>
          {loading ? '生成中...' : '生成预览'}
        </button>
        <button className="primary" type="button" onClick={sendReport} disabled={sending || loading}>
          {sending ? '发送中...' : '发送飞书'}
        </button>
      </div>
    </header>
  );
}

export function FeishuFlowGrid({
  analysisPayload,
  includeAi,
  sendMode
}: {
  analysisPayload: DailyFeishuAnalysisPayload | null;
  includeAi: boolean;
  sendMode: FeishuSendMode;
}) {
  const sendDescription = sendMode === 'text'
    ? (includeAi ? '发送文本时附带 AI 分析' : '手动发送当前日报文本')
    : (sendMode === 'card' ? '发送飞书原生交互卡片' : '优先发送交互卡片，失败时转文本');
  const cards = [
    ['01', 'Data Snapshot', '读取 Daily Metric 当前业务日数据', 'Ready'],
    ['02', 'LLM Insight', '让模型总结波动、异常和重点产品', analysisPayload ? (analysisPayload.configured ? 'Ready' : 'Needs Key') : 'Optional'],
    ['03', 'Native Card', '生成总览与产品线 Tab 看板', sendMode === 'text' ? 'Optional' : 'Ready'],
    ['04', 'Feishu Send', sendDescription, 'Ready']
  ];

  return (
    <section className="feishu-flow-grid" aria-label="AI 日报流程">
      {cards.map(([index, title, description, status]) => (
        <article className="feishu-flow-card" key={title}>
          <span>{index}</span>
          <strong>{title}</strong>
          <p>{description}</p>
          <small>{status}</small>
        </article>
      ))}
    </section>
  );
}
