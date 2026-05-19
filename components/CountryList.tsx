'use client';

import type { Country, Product } from '@/lib/types';
import { getCountryReelFarmCode } from '@/lib/utils';

const countryMapPins: Record<string, { lat: number; lon: number; flag: string }> = {
  US: { lat: 39.8, lon: -98.6, flag: '🇺🇸' },
  UK: { lat: 54.4, lon: -2.6, flag: '🇬🇧' },
  GE: { lat: 51.2, lon: 10.4, flag: '🇩🇪' },
  DE: { lat: 51.2, lon: 10.4, flag: '🇩🇪' },
  FR: { lat: 46.2, lon: 2.2, flag: '🇫🇷' },
  IT: { lat: 42.8, lon: 12.5, flag: '🇮🇹' },
  CA: { lat: 56.1, lon: -106.3, flag: '🇨🇦' },
  BR: { lat: -14.2, lon: -51.9, flag: '🇧🇷' },
  IN: { lat: 20.6, lon: 78.9, flag: '🇮🇳' },
  CN: { lat: 35.9, lon: 104.2, flag: '🇨🇳' },
  JP: { lat: 36.2, lon: 138.3, flag: '🇯🇵' },
  KR: { lat: 36.5, lon: 127.9, flag: '🇰🇷' },
  AU: { lat: -25.3, lon: 133.8, flag: '🇦🇺' }
};

function mapPinFor(country: Country) {
  const code = getCountryReelFarmCode(country);
  const pin = countryMapPins[code] || { lat: 0, lon: 0, flag: '🌐' };
  return {
    x: ((pin.lon + 180) / 360) * 100,
    y: ((90 - pin.lat) / 180) * 100,
    flag: pin.flag
  };
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
