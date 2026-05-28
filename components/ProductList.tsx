'use client';

import type { Product, ProductKpis } from '@/lib/types';
import { formatNumber, normalizeProductFolder } from '@/lib/utils';

export function ProductList({
  products,
  productKpis,
  onSelect,
  onAddProduct,
  onEditProduct
}: {
  products: Product[];
  productKpis: Record<string, ProductKpis | null>;
  onSelect: (product: Product) => void;
  onAddProduct: () => void;
  onEditProduct: (product: Product) => void;
}) {
  const groups = products.reduce<Record<string, Product[]>>((map, product) => {
    const folder = normalizeProductFolder(product);
    map[folder] = map[folder] || [];
    map[folder].push(product);
    return map;
  }, {});

  return (
    <section className="page active">
      <div className="section-head">
        <div>
          <h2>产品总览</h2>
        </div>
        <button className="btn primary" type="button" onClick={onAddProduct}>添加产品</button>
      </div>
      {Object.entries(groups).map(([folder, items]) => (
        <section className="product-folder" key={folder}>
          <h3>{folder}</h3>
          <div className="product-list">
            {items.map(product => {
              const kpis = productKpis[product.id];
              const stats = [
                {
                  icon: '♟',
                  label: 'Creators who posted',
                  today: Number(kpis?.today?.creators) || 0,
                  avg: Number(kpis?.seven_day?.average_creators) || 0
                },
                {
                  icon: '▤',
                  label: 'Posts published',
                  today: Number(kpis?.today?.posts) || 0,
                  avg: Number(kpis?.seven_day?.average_posts) || 0
                },
                {
                  icon: '◉',
                  label: 'Total views',
                  today: Number(kpis?.today?.views) || 0,
                  avg: Number(kpis?.seven_day?.average_views_per_day) || 0
                },
                {
                  icon: '♡',
                  label: 'Total likes',
                  today: Number(kpis?.today?.likes) || 0,
                  avg: Number(kpis?.seven_day?.average_likes) || 0
                }
              ];
              return (
                <article className="product-card" key={product.id}>
                  <div className="product-card-top">
                    <button className="product-main" type="button" onClick={() => onSelect(product)}>
                      <span className="product-logo product-logo-display">
                        {product.logo ? <img src={product.logo} alt="" /> : product.name?.slice(0, 1)}
                      </span>
                      <span className="product-card-copy">
                        <strong className="product-card-name">{product.name || '未命名产品'}</strong>
                        <span className="product-card-date">Last synced: {product.countries?.find(country => country.reelFarmSyncedAt)?.reelFarmSyncedAt?.slice(0, 10) || '—'}</span>
                      </span>
                    </button>
                    <div className="product-card-actions">
                      <span className="product-count-pill" title="账号数">👥 {formatNumber(product.creatorCount || 0)}</span>
                      <span className="product-count-pill" title="素材数">▤ {formatNumber(product.materialCount || 0)}</span>
                      <button
                        className="product-settings-btn"
                        type="button"
                        onClick={() => onEditProduct(product)}
                        title="产品设置"
                        aria-label={`${product.name || '产品'} 设置`}
                      >
                        ⋮
                      </button>
                    </div>
                  </div>
                  <div className="product-stat-grid">
                    {stats.map(stat => (
                      <div className="product-stat" key={stat.label}>
                        <span className="product-stat-icon">{stat.icon}</span>
                        <span className="product-stat-value"><strong>{formatNumber(stat.today)}</strong><small>/ {formatNumber(stat.avg)}</small></span>
                        <span className="product-stat-tooltip">
                          {stat.label}<br />
                          Yesterday: <b>{formatNumber(stat.today)}</b><br />
                          7d avg: <b>{formatNumber(stat.avg)}</b>
                        </span>
                      </div>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </section>
  );
}
