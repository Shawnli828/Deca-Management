'use client';

import type { Country, Product, ProductKpis } from '@/lib/types';
import { countryFlag, formatNumber, formatPercent } from '@/lib/utils';

export function CountryList({
  product,
  kpis,
  onBack,
  onSelect,
  onOpenSettings
}: {
  product: Product;
  kpis?: ProductKpis | null;
  onBack: () => void;
  onSelect: (country: Country) => void;
  onOpenSettings: () => void;
}) {
  const countries = product.countries || [];
  const todayAverageViews = Number(kpis?.today?.average_views) || 0;
  const sevenAverageViews = Number(kpis?.seven_day?.average_views) || 0;
  const sevenAverageEr = Number(kpis?.seven_day?.average_er) || 0;

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
        <button className="product-settings-btn inline" type="button" onClick={onOpenSettings} title="国家/地区设置" aria-label="国家/地区设置">⚙</button>
      </div>
      <div className="product-kpi-board">
        <div className="product-kpi-card today">
          <span>当日均播</span>
          <strong>{formatNumber(todayAverageViews)}</strong>
        </div>
        <div className="product-kpi-card views">
          <span>过去 7 日均播</span>
          <strong>{formatNumber(sevenAverageViews)}</strong>
        </div>
        <div className="product-kpi-card er">
          <span>过去 7 日平均 ER</span>
          <strong>{formatPercent(sevenAverageEr)}</strong>
        </div>
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
