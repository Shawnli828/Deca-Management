'use client';

import type { Country, Product } from '@/lib/types';
import { getCountryReelFarmCode } from '@/lib/utils';

export function CountryList({ product, onBack, onSelect }: { product: Product; onBack: () => void; onSelect: (country: Country) => void }) {
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
      </div>
      <div className="country-list">
        {(product.countries || []).map(country => (
          <button className="list-item" type="button" key={country.id} onClick={() => onSelect(country)}>
            <span className="country-code">{getCountryReelFarmCode(country)}</span>
            <span>
              <strong>{country.name}</strong>
              <span>{country.creatorCount || 0} 个账号 · {country.materialCount || 0} 个素材</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
