'use client';

import type { PublishAssignmentSort } from '@/lib/publishCheckFormatters';
import type { Product, PublishCheckAssignment } from '@/lib/types';
import { countryFlag } from '@/lib/utils';
import type { FormEventHandler } from 'react';

type PublishCheckPerson = {
  id: string;
  name: string;
};

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
