'use client';

import { formatPublishUtcTime, publishAccountLabel, type PublishAssignmentSort } from '@/lib/publishCheckFormatters';
import type { Product, PublishCheckAssignment, PublishCheckResult } from '@/lib/types';
import { countryFlag } from '@/lib/utils';
import type { FormEventHandler } from 'react';

type PublishCheckPerson = {
  id: string;
  name: string;
};

type PublishCheckGroup = NonNullable<PublishCheckResult['groups']>[number];

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

export function AssignmentForm({
  people,
  products,
  selectedProduct,
  personName,
  productId,
  countryId,
  onPersonNameChange,
  onProductChange,
  onCountryChange,
  onSubmit
}: {
  people: PublishCheckPerson[];
  products: Product[];
  selectedProduct?: Product;
  personName: string;
  productId: string;
  countryId: string;
  onPersonNameChange: (value: string) => void;
  onProductChange: (value: string) => void;
  onCountryChange: (value: string) => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
}) {
  return (
    <form className="assignment-form" onSubmit={onSubmit}>
      <input
        className="text-input"
        value={personName}
        list="publish-check-people"
        onChange={event => onPersonNameChange(event.target.value)}
        placeholder="负责人"
      />
      <datalist id="publish-check-people">
        {people.map(person => <option value={person.name} key={person.id} />)}
      </datalist>
      <select className="text-input" value={productId} onChange={event => onProductChange(event.target.value)}>
        {products.map(product => <option value={product.id} key={product.id}>{product.name}</option>)}
      </select>
      <select className="text-input" value={countryId} onChange={event => onCountryChange(event.target.value)}>
        {(selectedProduct?.countries || []).map(country => <option value={country.id} key={country.id}>{country.name}</option>)}
      </select>
      <button className="btn ghost" type="submit">添加范围</button>
    </form>
  );
}

export function AssignmentTable({
  assignments,
  products,
  peopleById,
  assignmentSort,
  onSortChange,
  onRemove
}: {
  assignments: PublishCheckAssignment[];
  products: Product[];
  peopleById: Map<string, PublishCheckPerson>;
  assignmentSort: PublishAssignmentSort;
  onSortChange: (sort: PublishAssignmentSort) => void;
  onRemove: (id: string) => void;
}) {
  return (
    <div className="assignment-table">
      <div className="assignment-table-head">
        <button className={assignmentSort === 'person' ? 'active' : ''} type="button" onClick={() => onSortChange('person')}>负责人 ↕</button>
        <button className={assignmentSort === 'product' ? 'active' : ''} type="button" onClick={() => onSortChange('product')}>产品 ↕</button>
        <button className={assignmentSort === 'country' ? 'active' : ''} type="button" onClick={() => onSortChange('country')}>国家/地区 ↕</button>
        <span>操作</span>
      </div>
      <div className="assignment-list">
        {assignments.length ? assignments.map(item => (
          <AssignmentRow
            key={item.id}
            item={item}
            products={products}
            peopleById={peopleById}
            onRemove={onRemove}
          />
        )) : <div className="empty-state">还没有配置负责范围。</div>}
      </div>
    </div>
  );
}

function AssignmentRow({
  item,
  products,
  peopleById,
  onRemove
}: {
  item: PublishCheckAssignment;
  products: Product[];
  peopleById: Map<string, PublishCheckPerson>;
  onRemove: (id: string) => void;
}) {
  const product = products.find(entry => entry.id === item.product_id);
  const country = product?.countries?.find(entry => entry.id === item.country_id);

  return (
    <div className="assignment-row">
      <div className="assignment-cell">
        <strong>{item.person_name || peopleById.get(item.person_id)?.name || '未命名'}</strong>
      </div>
      <div className="assignment-cell">
        <span className="assignment-product-value">
          <span className="assignment-product-logo">
            {product?.logo ? <img src={product.logo} alt="" /> : product?.name?.slice(0, 1) || '?'}
          </span>
          <strong>{product?.name || '未知产品'}</strong>
        </span>
      </div>
      <div className="assignment-cell">
        <strong>{country ? countryFlag(country) : '🌐'} {country?.name || '未知地区'}</strong>
      </div>
      <div className="assignment-actions">
        <button className="btn danger" type="button" onClick={() => onRemove(item.id)}>删除</button>
      </div>
    </div>
  );
}

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
