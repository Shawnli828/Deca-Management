'use client';

import type { Country, Product } from '@/lib/types';
import { getCountryReelFarmCode } from '@/lib/utils';

const countryMapPins: Record<string, { x: number; y: number; flag: string }> = {
  US: { x: 22, y: 42, flag: '🇺🇸' },
  UK: { x: 46, y: 34, flag: '🇬🇧' },
  GE: { x: 49, y: 38, flag: '🇩🇪' },
  DE: { x: 49, y: 38, flag: '🇩🇪' },
  FR: { x: 47, y: 42, flag: '🇫🇷' },
  IT: { x: 50, y: 47, flag: '🇮🇹' },
  CA: { x: 20, y: 28, flag: '🇨🇦' },
  BR: { x: 34, y: 68, flag: '🇧🇷' },
  IN: { x: 67, y: 55, flag: '🇮🇳' },
  CN: { x: 72, y: 45, flag: '🇨🇳' },
  JP: { x: 82, y: 44, flag: '🇯🇵' },
  KR: { x: 78, y: 43, flag: '🇰🇷' },
  AU: { x: 79, y: 76, flag: '🇦🇺' }
};

function mapPinFor(country: Country) {
  const code = getCountryReelFarmCode(country);
  return countryMapPins[code] || { x: 52, y: 50, flag: '🌐' };
}

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
      <section className="country-map-panel" aria-label="国家/地区地图">
        <div className="world-map">
          <svg className="world-map-svg" viewBox="0 0 1000 500" aria-hidden="true">
            <path d="M116 150 205 108 310 130 338 203 270 246 158 230 92 190Z" />
            <path d="M242 260 322 282 354 372 316 448 250 410 220 326Z" />
            <path d="M430 138 514 110 602 146 578 214 468 210 390 178Z" />
            <path d="M520 218 598 236 640 330 594 410 526 336Z" />
            <path d="M622 150 748 128 874 184 810 252 690 230 592 194Z" />
            <path d="M734 315 844 338 906 410 820 454 710 410Z" />
          </svg>
          {countries.map(country => {
            const pin = mapPinFor(country);
            return (
              <button
                className="country-map-pin"
                type="button"
                key={country.id}
                style={{ left: `${pin.x}%`, top: `${pin.y}%` }}
                onClick={() => onSelect(country)}
                aria-label={`打开 ${country.name}`}
              >
                <span className="country-map-flag">{pin.flag}</span>
                <span className="country-map-code">{getCountryReelFarmCode(country)}</span>
              </button>
            );
          })}
        </div>
      </section>
      <div className="country-list">
        {countries.map(country => (
          <button className="list-item country-list-item" type="button" key={country.id} onClick={() => onSelect(country)}>
            <span className="country-code">{getCountryReelFarmCode(country)}</span>
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
