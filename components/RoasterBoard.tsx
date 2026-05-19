'use client';

import type { Product, RoasterState } from '@/lib/types';
import { createPersonId, normalizeProductFolder } from '@/lib/utils';
import { FormEvent, useState } from 'react';

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

  function addPerson(event: FormEvent) {
    event.preventDefault();
    const clean = name.trim();
    if (!clean) return;
    onChange({ ...state, people: [...state.people, { id: createPersonId(clean), name: clean }] });
    setName('');
  }

  function toggle(productId: string, role: string, personId: string) {
    const assignments = { ...state.assignments };
    assignments[productId] = { ...(assignments[productId] || {}) };
    const current = assignments[productId][role] || [];
    assignments[productId][role] = current.includes(personId) ? current.filter(id => id !== personId) : [...current, personId];
    onChange({ ...state, assignments });
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
        {state.people.map(person => <span className="person-chip" key={person.id}>{person.name}</span>)}
      </div>
      <div className="roaster-table-wrap">
        <table className="roaster-table">
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
                  return (
                    <td key={role.key}>
                      <div className={`roaster-dropzone ${assigned.length ? '' : 'is-empty'}`}>
                        {state.people.map(person => (
                          <button type="button" className={`person-chip ${assigned.includes(person.id) ? 'active' : ''}`} key={person.id} onClick={() => toggle(product.id, role.key, person.id)}>{person.name}</button>
                        ))}
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
