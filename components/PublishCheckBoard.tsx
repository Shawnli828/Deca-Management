'use client';

import type { Product, PublishCheckAccount, PublishCheckAssignment, PublishCheckState, RoasterState } from '@/lib/types';
import { countryFlag } from '@/lib/utils';
import { FormEvent, useEffect, useMemo, useState } from 'react';

function accountLabel(account: PublishCheckAccount) {
  return account.username || account.display_name || account.reelfarm_account_id || account.account_id || 'Unknown account';
}

function formatTime(value?: string) {
  if (!value) return '暂无记录';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getUTCFullYear()}/${String(date.getUTCMonth() + 1).padStart(2, '0')}/${String(date.getUTCDate()).padStart(2, '0')} ${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')} UTC`;
}

export function PublishCheckBoard({
  products,
  roaster,
  state,
  running,
  onSave,
  onRun
}: {
  products: Product[];
  roaster: RoasterState;
  state: PublishCheckState;
  running: boolean;
  onSave: (state: PublishCheckState) => Promise<void>;
  onRun: () => Promise<void>;
}) {
  const [personId, setPersonId] = useState(roaster.people[0]?.id || '');
  const [productId, setProductId] = useState(products[0]?.id || '');
  const selectedProduct = products.find(product => product.id === productId) || products[0];
  const [countryId, setCountryId] = useState(selectedProduct?.countries?.[0]?.id || '');
  const [assignmentSort, setAssignmentSort] = useState<'person' | 'product' | 'country'>('person');
  const result = state.last_result;

  const peopleById = useMemo(() => new Map(roaster.people.map(person => [person.id, person])), [roaster.people]);
  const sortedAssignments = useMemo(() => {
    return [...state.assignments].sort((left, right) => {
      const leftProduct = products.find(product => product.id === left.product_id);
      const rightProduct = products.find(product => product.id === right.product_id);
      const leftCountry = leftProduct?.countries?.find(country => country.id === left.country_id);
      const rightCountry = rightProduct?.countries?.find(country => country.id === right.country_id);
      const values = {
        person: [left.person_name, right.person_name],
        product: [leftProduct?.name || '', rightProduct?.name || ''],
        country: [leftCountry?.name || '', rightCountry?.name || '']
      }[assignmentSort];
      const primary = String(values[0] || '').localeCompare(String(values[1] || ''), 'zh-Hans');
      if (primary !== 0) return primary;
      return String(left.person_name || '').localeCompare(String(right.person_name || ''), 'zh-Hans');
    });
  }, [assignmentSort, products, state.assignments]);

  useEffect(() => {
    if (!personId && roaster.people[0]?.id) setPersonId(roaster.people[0].id);
    if (!productId && products[0]?.id) {
      setProductId(products[0].id);
      setCountryId(products[0].countries?.[0]?.id || '');
    }
  }, [personId, productId, products, roaster.people]);

  function addAssignment(event: FormEvent) {
    event.preventDefault();
    const product = products.find(item => item.id === productId);
    const country = product?.countries?.find(item => item.id === countryId);
    const person = peopleById.get(personId);
    if (!product || !country || !person) return;

    const exists = state.assignments.some(item => item.person_id === person.id && item.product_id === product.id && item.country_id === country.id);
    if (exists) return;

    const assignment: PublishCheckAssignment = {
      id: crypto.randomUUID(),
      person_id: person.id,
      person_name: person.name,
      product_id: product.id,
      country_id: country.id
    };
    onSave({ ...state, assignments: [...state.assignments, assignment] });
  }

  function removeAssignment(id: string) {
    onSave({ ...state, assignments: state.assignments.filter(item => item.id !== id) });
  }

  function changeProduct(nextProductId: string) {
    setProductId(nextProductId);
    const product = products.find(item => item.id === nextProductId);
    setCountryId(product?.countries?.[0]?.id || '');
  }

  return (
    <section className="publish-check-board">
      <div className="publish-check-hero">
        <div>
          <h2>每日发布检查</h2>
          <p>每天北京时间 23:00 自动检查，也可以随时手动检查今天各负责人范围内的账号是否发布。</p>
        </div>
        <button className="btn primary" type="button" onClick={onRun} disabled={running}>
          {running ? '检查中...' : '立即检查'}
        </button>
      </div>

      <div className="publish-check-window">
        <span>北京时间日期：{result?.beijing_date || '待检查'}</span>
        <span>UTC 区间：{result?.utc_window?.start || '--'} → {result?.utc_window?.end || '--'}</span>
      </div>

      <section className="publish-check-panel">
        <div className="publish-check-panel-head">
          <div>
            <h3>负责范围</h3>
            <p>配置每个人负责的产品和国家/地区。</p>
          </div>
        </div>
        <form className="assignment-form" onSubmit={addAssignment}>
          <select className="text-input" value={personId} onChange={event => setPersonId(event.target.value)}>
            {roaster.people.map(person => <option value={person.id} key={person.id}>{person.name}</option>)}
          </select>
          <select className="text-input" value={productId} onChange={event => changeProduct(event.target.value)}>
            {products.map(product => <option value={product.id} key={product.id}>{product.name}</option>)}
          </select>
          <select className="text-input" value={countryId} onChange={event => setCountryId(event.target.value)}>
            {(selectedProduct?.countries || []).map(country => <option value={country.id} key={country.id}>{country.name}</option>)}
          </select>
          <button className="btn ghost" type="submit">添加范围</button>
        </form>
        <div className="assignment-table">
          <div className="assignment-table-head">
            <button className={assignmentSort === 'person' ? 'active' : ''} type="button" onClick={() => setAssignmentSort('person')}>负责人 ↕</button>
            <button className={assignmentSort === 'product' ? 'active' : ''} type="button" onClick={() => setAssignmentSort('product')}>产品 ↕</button>
            <button className={assignmentSort === 'country' ? 'active' : ''} type="button" onClick={() => setAssignmentSort('country')}>国家/地区 ↕</button>
            <span>操作</span>
          </div>
          <div className="assignment-list">
          {sortedAssignments.length ? sortedAssignments.map(item => {
            const product = products.find(entry => entry.id === item.product_id);
            const country = product?.countries?.find(entry => entry.id === item.country_id);
            return (
              <div className="assignment-row" key={item.id}>
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
                  <button className="btn danger" type="button" onClick={() => removeAssignment(item.id)}>删除</button>
                </div>
              </div>
            );
          }) : <div className="empty-state">还没有配置负责范围。</div>}
          </div>
        </div>
      </section>

      <section className="publish-check-panel">
        <div className="publish-check-panel-head">
          <div>
            <h3>检查结果</h3>
            <p>只展示没有在北京时间当天发布的账号；全部正常的范围会显示通过。</p>
          </div>
          <div className="publish-check-summary">
            <strong>{result?.totals?.missing_accounts || 0}</strong>
            <span>未发布账号</span>
          </div>
        </div>
        <div className="publish-result-grid">
          {result?.groups?.length ? result.groups.map(group => (
            <article className={`publish-result-card ${group.missing_account_count ? 'has-missing' : 'is-clear'}`} key={group.assignment_id}>
              <div className="publish-result-card-head">
                <div>
                  <strong>{group.person_name}</strong>
                  <span>{group.product?.name} · {group.country?.name}</span>
                </div>
                <span className="publish-result-count">{group.missing_account_count ? `${group.missing_account_count} 未发布` : '已发布'}</span>
              </div>
              {group.missing_accounts.length ? (
                <div className="missing-account-list">
                  {group.missing_accounts.map(account => (
                    <div className="missing-account-row" key={`${account.account_id}-${account.automation_id}`}>
                      <div>
                        <strong>@{accountLabel(account).replace(/^@/, '')}</strong>
                        <span>{account.automation_name || account.reelfarm_automation_id || '无 automation 名称'}</span>
                      </div>
                      <span>最近发布：{formatTime(account.latest_post_at)}</span>
                    </div>
                  ))}
                </div>
              ) : <div className="empty-state">这个范围今天都有发布。</div>}
            </article>
          )) : <div className="empty-state">还没有检查结果，点击「立即检查」生成今天的巡检。</div>}
        </div>
      </section>
    </section>
  );
}
