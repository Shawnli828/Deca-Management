'use client';

import { formatPublishUtcTime, publishAccountLabel } from '@/lib/publishCheckFormatters';
import type { PublishCheckResult } from '@/lib/types';

type PublishCheckGroup = NonNullable<PublishCheckResult['groups']>[number];

export function PublishResultPanel({
  result,
  sendingReminder,
  expandedResultCards,
  onSendReminder,
  onToggleResultCard
}: {
  result?: PublishCheckResult | null;
  sendingReminder: boolean;
  expandedResultCards: Record<string, boolean>;
  onSendReminder: () => Promise<void>;
  onToggleResultCard: (id: string) => void;
}) {
  return (
    <section className="publish-check-panel">
      <div className="publish-check-panel-head">
        <div>
          <h3>检查结果</h3>
          <p>只展示没有在北京时间当天发布的账号；全部正常的范围会显示通过。</p>
        </div>
        <div className="publish-result-actions">
          <button className="btn ghost" type="button" onClick={onSendReminder} disabled={sendingReminder || !result}>
            {sendingReminder ? '发送中...' : '发送飞书提醒'}
          </button>
          <div className="publish-check-summary">
            <strong>{result?.totals?.missing_accounts || 0}</strong>
            <span>未发布账号</span>
          </div>
        </div>
      </div>
      <div className="publish-result-grid">
        {result?.groups?.length ? result.groups.map(group => (
          <PublishResultCard
            key={group.assignment_id}
            group={group}
            expanded={Boolean(expandedResultCards[String(group.assignment_id || '')])}
            onToggle={() => onToggleResultCard(String(group.assignment_id || ''))}
          />
        )) : <div className="empty-state">还没有检查结果，点击「立即检查」生成今天的巡检。</div>}
      </div>
    </section>
  );
}

function PublishResultCard({
  group,
  expanded,
  onToggle
}: {
  group: PublishCheckGroup;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <article className={`publish-result-card ${group.missing_account_count ? 'has-missing' : 'is-clear'}`}>
      <button className="publish-result-card-head" type="button" onClick={onToggle}>
        <div>
          <strong>{group.person_name}</strong>
          <span>{group.product?.name} · {group.country?.name}</span>
        </div>
        <span className="publish-result-count">{group.missing_account_count ? `${group.missing_account_count} 未发布` : '已发布'}</span>
      </button>
      {expanded && group.missing_accounts.length ? (
        <div className="missing-account-list">
          {group.missing_accounts.map(account => (
            <div className="missing-account-row" key={`${account.account_id}-${account.automation_id}`}>
              <div>
                <strong>@{publishAccountLabel(account).replace(/^@/, '')}</strong>
                <span>{account.automation_name || account.reelfarm_automation_id || '无 automation 名称'}</span>
              </div>
              <span>最近发布：{formatPublishUtcTime(account.latest_post_at)}</span>
            </div>
          ))}
        </div>
      ) : null}
      {expanded && !group.missing_accounts.length ? <div className="empty-state">这个范围今天都有发布。</div> : null}
    </article>
  );
}
