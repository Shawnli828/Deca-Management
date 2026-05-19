'use client';

import type { Product } from '@/lib/types';

export function MetricsBar({ products }: { products: Product[] }) {
  const countries = products.reduce((sum, product) => sum + (product.countries?.length || 0), 0);
  const concepts = products.reduce((sum, product) => sum + (product.countries || []).reduce((inner, country) => inner + (country.concepts?.length || 0), 0), 0);
  const total = products.reduce((sum, product) => sum + (product.countries || []).reduce((inner, country) => inner + (country.concepts || []).reduce((value, concept) => value + (Number(concept.count) || 0), 0), 0), 0);
  const rows = [['产品', products.length], ['国家/地区', countries], ['创意', concepts], ['数量', total]];

  return (
    <section className="metrics">
      {rows.map(([label, value]) => (
        <div className="metric-card" key={label}>
          <div className="metric-label">{label}</div>
          <div className="metric-value">{value}</div>
        </div>
      ))}
    </section>
  );
}
