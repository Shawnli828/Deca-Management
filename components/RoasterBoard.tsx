'use client';

import type { Product, RoasterState } from '@/lib/types';
import { createPersonId, normalizeProductFolder } from '@/lib/utils';
import { DragEvent, FormEvent, useMemo, useState } from 'react';

const roles = [
  { key: 'leader', label: 'Leader', group: '负责人' },
  { key: 'pm', label: 'PM', group: '负责人' },
  { key: 'backend', label: '后台', group: '负责人' },
  { key: 'slideshow', label: 'Slideshow', group: '执行人' },
  { key: 'shortVideo', label: 'Short video', group: '执行人' },
  { key: 'reddit', label: 'Reddit', group: '执行人' },
  { key: 'seo', label: 'SEO', group: '执行人' },
  { key: 'twitter', label: 'Twitter', group: '执行人' },
  { key: 'influencer', label: 'Influencer', group: '执行人' }
];

export function RoasterBoard({ products, state, onChange }: { products: Product[]; state: RoasterState; onChange: (state: RoasterState) => void }) {
  const [name, setName] = useState('');
  const peopleById = useMemo(() => new Map(state.people.map(person => [person.id, person])), [state.people]);

  function addPerson(event: FormEvent) {
    event.preventDefault();
    const clean = name.trim();
    if (!clean) return;
    onChange({ ...state, people: [...state.people, { id: createPersonId(clean), name: clean }] });
    setName('');
  }

  function assign(productId: string, role: string, personId: string) {
    if (!peopleById.has(personId)) return;
    const assignments = { ...state.assignments };
    assignments[productId] = { ...(assignments[productId] || {}) };
    const current = assignments[productId][role] || [];
    if (current.includes(personId)) return;
    assignments[productId][role] = [...current, personId];
    onChange({ ...state, assignments });
  }

  function unassign(productId: string, role: string, personId: string) {
    const assignments = { ...state.assignments };
    assignments[productId] = { ...(assignments[productId] || {}) };
    assignments[productId][role] = (assignments[productId][role] || []).filter(id => id !== personId);
    onChange({ ...state, assignments });
  }

  function removePerson(personId: string) {
    const assignments: RoasterState['assignments'] = {};
    Object.entries(state.assignments || {}).forEach(([productId, roleMap]) => {
      assignments[productId] = {};
      Object.entries(roleMap || {}).forEach(([role, personIds]) => {
        assignments[productId][role] = personIds.filter(id => id !== personId);
      });
    });
    onChange({ people: state.people.filter(person => person.id !== personId), assignments });
  }

  function handleDragStart(event: DragEvent<HTMLSpanElement>, personId: string) {
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('application/x-deca-person-id', personId);
    event.dataTransfer.setData('text/plain', personId);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, productId: string, role: string) {
    event.preventDefault();
    const personId = event.dataTransfer.getData('application/x-deca-person-id') || event.dataTransfer.getData('text/plain');
    assign(productId, role, personId);
  }

  function toneFor(personId: string) {
    const seed = personId.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
    return `tone-${(seed % 5) + 1}`;
  }

  return (
    <section className="roaster-board">
      <div className="roaster-toolbar">
        <form className="roaster-person-form" onSubmit={addPerson}>
          <input className="text-input" value={name} onChange={event => setName(event.target.value)} placeholder="添加人员" />
          <button className="btn primary" type="submit">添加</button>
        </form>
      </div>
      <div className="roaster-people">
        {state.people.length ? state.people.map(person => (
          <span
            className={`person-chip ${toneFor(person.id)}`}
            draggable
            key={person.id}
            onDragStart={event => handleDragStart(event, person.id)}
            title="拖到角色格子里分配"
          >
            <span className="person-avatar">{person.name.slice(0, 1).toUpperCase()}</span>
            <span className="person-name">{person.name}</span>
            <button className="person-chip-delete" type="button" onClick={() => removePerson(person.id)} aria-label={`删除 ${person.name}`}>×</button>
          </span>
        )) : <span className="roaster-empty-people">先添加人员，再拖入下面的角色格子。</span>}
      </div>
      <div className="roaster-table-wrap">
        <table className="roaster-table">
          <colgroup>
            <col className="roaster-col-attr" />
            <col className="roaster-col-product" />
            {roles.map(role => <col className="roaster-col-role" key={role.key} />)}
          </colgroup>
          <thead>
            <tr className="roaster-group-row">
              <th></th>
              <th></th>
              <th colSpan={3}>负责人</th>
              <th colSpan={6}>执行人</th>
            </tr>
            <tr>
              <th>属性</th>
              <th>产品</th>
              {roles.map(role => <th key={role.key}>{role.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {products.map(product => (
              <tr key={product.id}>
                <td className="roaster-attr">{normalizeProductFolder(product)}</td>
                <td className="roaster-product"><div className="roaster-product-cell"><span className="roaster-product-logo">{product.logo ? <img src={product.logo} alt="" /> : product.name?.slice(0, 1)}</span><span className="roaster-app-name">{product.name}</span></div></td>
                {roles.map(role => {
                  const assigned = state.assignments?.[product.id]?.[role.key] || [];
                  const assignedPeople = assigned.map(personId => peopleById.get(personId)).filter(Boolean) as Array<{ id: string; name: string }>;
                  return (
                    <td key={role.key}>
                      <div
                        className={`roaster-dropzone ${assignedPeople.length ? '' : 'is-empty'}`}
                        onDragOver={event => event.preventDefault()}
                        onDrop={event => handleDrop(event, product.id, role.key)}
                      >
                        {assignedPeople.length ? assignedPeople.map(person => (
                          <span className={`person-chip assignment-chip ${toneFor(person.id)}`} key={person.id}>
                            <span className="person-avatar">{person.name.slice(0, 1).toUpperCase()}</span>
                            <span className="person-name">{person.name}</span>
                            <button className="person-chip-remove" type="button" onClick={() => unassign(product.id, role.key, person.id)} aria-label={`移除 ${person.name}`}>×</button>
                          </span>
                        )) : <span className="roaster-empty-cell-label">拖入人员</span>}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
