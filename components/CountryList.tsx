'use client';

import type { Country, Product } from '@/lib/types';
import { countryFlag } from '@/lib/utils';

export function CountryList({
  product,
  onBack,
  onSelect,
  onAdd
}: {
  product: Product;
  onBack: () => void;
  onSelect: (country: Country) => void;
  onAdd: (product: Product) => void;
}) {
  const countries = product.countries || [];

  return (
    <section className="page active">
      <nav className="breadcrumbs">
        <button className="crumb-btn" onClick={onBack}>产品总览</button>
        <span>/</span>
        <strong>{product.name}</strong>
      </nav>
      <div className="section-head">
        <div>
          <h2>{product.name}</h2>
          <p>选择国家/地区后查看账号和素材。</p>
        </div>
        <button className="btn primary" type="button" onClick={() => onAdd(product)}>添加地区</button>
      </div>
      <div className="country-list">
        {countries.map(country => (
          <button className="list-item country-list-item" type="button" key={country.id} onClick={() => onSelect(country)}>
            <span className="country-code" aria-hidden="true">{countryFlag(country)}</span>
            <span className="country-copy">
              <strong className="country-name">{country.name || '未命名地区'}</strong>
              <span className="country-meta">{country.creatorCount || 0} 个账号 · {country.materialCount || 0} 个素材</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
