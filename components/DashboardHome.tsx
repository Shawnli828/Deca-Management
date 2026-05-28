'use client';

import type { Product } from '@/lib/types';
import { formatNumber } from '@/lib/utils';

export function DashboardHome({
  products
}: {
  products: Product[];
}) {
  const countries = products.reduce((sum, product) => sum + (product.countries?.length || 0), 0);
  const accounts = products.reduce((sum, product) => sum + (Number(product.creatorCount) || 0), 0);
  const materials = products.reduce((sum, product) => sum + (Number(product.materialCount) || 0), 0);
  const topProducts = [...products]
    .sort((left, right) => (Number(right.materialCount) || 0) - (Number(left.materialCount) || 0))
    .slice(0, 4);

  const metrics = [
    { label: 'Products', value: products.length, tone: 'blue' },
    { label: 'Countries', value: countries, tone: 'violet' },
    { label: 'Accounts', value: accounts, tone: 'green' },
    { label: 'Materials', value: materials, tone: 'amber' }
  ];

  return (
    <section className="dashboard-home">
      <header className="dashboard-hero">
        <div>
          <p className="dashboard-kicker">Welcome to</p>
          <h1>Deca Growth</h1>
        </div>
      </header>

      <div className="dashboard-metrics">
        {metrics.map(metric => (
          <article className={`dashboard-metric ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{formatNumber(metric.value)}</strong>
          </article>
        ))}
      </div>

      <section className="dashboard-overview-card">
        <div>
          <h2>Product Snapshot</h2>
          <p>当前中台已接入的产品与素材规模。</p>
        </div>
        <div className="dashboard-product-list">
          {topProducts.length ? topProducts.map(product => (
            <article className="dashboard-product-row" key={product.id}>
              <span className="dashboard-product-logo">
                {product.logo ? <img src={product.logo} alt="" /> : product.name.slice(0, 2).toUpperCase()}
              </span>
              <span>
                <strong>{product.name}</strong>
                <small>{formatNumber(product.countries?.length || 0)} 个国家/地区 · {formatNumber(product.creatorCount || 0)} 个账号 · {formatNumber(product.materialCount || 0)} 个素材</small>
              </span>
            </article>
          )) : (
            <p className="dashboard-empty">暂无产品数据。</p>
          )}
        </div>
      </section>
    </section>
  );
}
