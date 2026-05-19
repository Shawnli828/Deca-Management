'use client';

import type { Product } from '@/lib/types';

export function MetricsBar({ products }: { products: Product[] }) {
  const countries = products.reduce((sum, product) => sum + (product.countries?.length || 0), 0);
  const creators = products.reduce((sum, product) => sum + (Number(product.creatorCount) || 0), 0);
  const materials = products.reduce((sum, product) => sum + (Number(product.materialCount) || 0), 0);
  const rows = [['产品', products.length], ['国家/地区', countries], ['数量', creators], ['素材', materials]];

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
