'use client';

import type { PublishCheckResult } from '@/lib/types';

export function PublishCheckHero({
  running,
  onRun
}: {
  running: boolean;
  onRun: () => Promise<void>;
}) {
  return (
    <div className="publish-check-hero">
      <div>
        <h2>每日发布检查</h2>
        <p>每天北京时间 23:00 自动检查，也可以随时手动检查今天各负责人范围内的账号是否发布。</p>
      </div>
      <button className="btn primary" type="button" onClick={onRun} disabled={running}>
        {running ? '检查中...' : '立即检查'}
      </button>
    </div>
  );
}

export function PublishCheckWindow({
  result
}: {
  result?: PublishCheckResult | null;
}) {
  return (
    <div className="publish-check-window">
      <span>北京时间日期：{result?.beijing_date || '待检查'}</span>
      <span>UTC 区间：{result?.utc_window?.start || '--'} → {result?.utc_window?.end || '--'}</span>
    </div>
  );
}
