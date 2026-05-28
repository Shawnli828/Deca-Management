'use client';

import type { Product } from '@/lib/types';
import { formatNumber } from '@/lib/utils';

export function DashboardHome({
  products,
  status,
  statusError,
  syncAllRunning,
  syncAllProgress,
  onSyncAll,
  onOpenDatabase,
  onReset
}: {
  products: Product[];
  status: string;
  statusError: boolean;
  syncAllRunning: boolean;
  syncAllProgress: string;
  onSyncAll: () => void;
  onOpenDatabase: () => void;
  onReset: () => void;
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
          <p>One cockpit for product growth, creator pools, publishing checks, and content intelligence.</p>
        </div>
        <div className="dashboard-actions">
          <span className={`status-pill ${statusError ? 'error' : ''}`}>{status}</span>
          <button className="btn ghost" type="button" onClick={onSyncAll} disabled={syncAllRunning || !products.length}>
            {syncAllRunning ? `同步全部 ${syncAllProgress}` : '同步全部'}
          </button>
          <button className="btn ghost" type="button" onClick={onOpenDatabase}>打开数据库</button>
          <button className="btn ghost" type="button" onClick={onReset}>恢复示例</button>
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
