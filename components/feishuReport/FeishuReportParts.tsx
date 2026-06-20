'use client';

import { localIsoDate } from '@/lib/feishuReportHelpers';
import type { DailyFeishuAnalysisPayload } from '@/lib/types';

type FeishuReportHeroProps = {
  reportDate: string;
  setReportDate: (value: string) => void;
  loading: boolean;
  sending: boolean;
  loadPreview: (date: string) => void;
  sendReport: () => void;
};

export function FeishuReportHero({
  reportDate,
  setReportDate,
  loading,
  sending,
  loadPreview,
  sendReport
}: FeishuReportHeroProps) {
  return (
    <header className="feishu-report-hero">
      <div>
        <p className="dashboard-kicker">AI Feishu Report</p>
        <h1>Feishu Report</h1>
        <p>每日业务数据先在这里生成可检查文本；后续可以接入 LLM 洞察、图片渲染，再一起发送到飞书。</p>
      </div>
      <div className="feishu-report-actions">
        <label>
          <span>业务日</span>
          <input type="date" value={reportDate} max={localIsoDate()} onChange={event => setReportDate(event.target.value)} />
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
  includeAi
}: {
  analysisPayload: DailyFeishuAnalysisPayload | null;
  includeAi: boolean;
}) {
  const cards = [
    ['01', 'Data Snapshot', '读取 Daily Metric 当前业务日数据', 'Ready'],
    ['02', 'LLM Insight', '让模型总结波动、异常和重点产品', analysisPayload ? (analysisPayload.configured ? 'Ready' : 'Needs Key') : 'Optional'],
    ['03', 'Image Render', '后续把总结渲染成日报图片', 'Planned'],
    ['04', 'Feishu Send', includeAi ? '发送文本时附带 AI 分析' : '手动发送当前日报文本', 'Ready']
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
