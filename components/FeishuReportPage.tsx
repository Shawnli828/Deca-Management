'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { DailyFeishuPreviewPayload, DailyFeishuReport, DailyFeishuSendResult } from '@/lib/types';
import { formatNumber } from '@/lib/utils';

function localIsoDate(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function metric(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return formatNumber(value);
}

function percent(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number.toFixed(2)}%`;
}

function ratio(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return number;
}

function reportTotals(report?: DailyFeishuReport | null) {
  return report?.totals || {};
}

export function FeishuReportPage() {
  const [reportDate, setReportDate] = useState(localIsoDate(-1));
  const [payload, setPayload] = useState<DailyFeishuPreviewPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [sendResult, setSendResult] = useState<DailyFeishuSendResult | null>(null);

  const totals = useMemo(() => reportTotals(payload?.report), [payload]);
  const products = payload?.report?.products || [];
  const downloadRate = ratio(totals.download_rate);

  async function loadPreview(nextDate = reportDate) {
    setLoading(true);
    setError('');
    setSendResult(null);
    try {
      const next = await api.dailyFeishuPreview(nextDate);
      setPayload(next);
    } catch (previewError: any) {
      setError(previewError?.message || '日报预览读取失败');
    } finally {
      setLoading(false);
    }
  }

  async function sendReport() {
    setSending(true);
    setError('');
    setSendResult(null);
    try {
      const result = await api.sendDailyFeishuReport(reportDate);
      setSendResult(result);
      await loadPreview(reportDate);
    } catch (sendError: any) {
      setError(sendError?.message || '飞书发送失败');
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    void loadPreview(reportDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="feishu-report-page">
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

      {error ? <div className="growth-error">{error}</div> : null}
      {sendResult?.ok ? <div className="feishu-success">已发送到飞书：{sendResult.sent_at || '刚刚'}</div> : null}

      <section className="feishu-flow-grid" aria-label="AI 日报流程">
        {[
          ['01', 'Data Snapshot', '读取 Daily Metric 当前业务日数据', 'Ready'],
          ['02', 'LLM Insight', '后续让模型总结波动、异常和重点产品', 'Planned'],
          ['03', 'Image Render', '后续把总结渲染成日报图片', 'Planned'],
          ['04', 'Feishu Send', '手动发送当前文本，自动发送仍沿用现有任务', 'Ready']
        ].map(([index, title, description, status]) => (
          <article className="feishu-flow-card" key={title}>
            <span>{index}</span>
            <strong>{title}</strong>
            <p>{description}</p>
            <small>{status}</small>
          </article>
        ))}
      </section>

      <section className="feishu-report-summary">
        {[
          ['总播放', totals.total_views],
          ['ReelFarm', totals.reelfarm_views],
          ['Clone', totals.clone_views],
          ['Onboarding Unique', totals.downloads],
          ['下载/播放', downloadRate === null ? null : `${downloadRate.toFixed(2)}%`]
        ].map(([label, value]) => (
          <article key={label as string}>
            <span>{label}</span>
            <strong>{typeof value === 'string' ? value : metric(value)}</strong>
          </article>
        ))}
      </section>

      <div className="feishu-report-layout">
        <section className="feishu-message-card">
          <div className="feishu-card-head">
            <div>
              <h2>飞书消息预览</h2>
              <p>
                业务日 {payload?.report?.report_date || reportDate} · 内容窗口{' '}
                {payload?.report?.business_window_local?.start || '—'} → {payload?.report?.business_window_local?.end || '—'}
              </p>
            </div>
          </div>
          <pre className="feishu-message-preview">{payload?.message || (loading ? '正在生成...' : '暂无预览')}</pre>
        </section>

        <aside className="feishu-product-card">
          <div className="feishu-card-head">
            <div>
              <h2>产品拆分</h2>
              <p>用于检查发送前每个产品的数据是否合理。</p>
            </div>
          </div>
          <div className="feishu-product-list">
            {products.length ? products.map(product => (
              <article key={String(product.product_code || product.product_name)}>
                <div>
                  <strong>{String(product.product_name || product.product_code || 'Product')}</strong>
                  <span>{String(product.product_code || '')}</span>
                </div>
                <small>播放 {metric(product.total_views)} · Onboarding {metric(product.downloads)}</small>
              </article>
            )) : (
              <p className="feishu-empty">暂无产品数据。</p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
