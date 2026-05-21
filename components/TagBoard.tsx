'use client';

import type { Product, TagDashboard } from '@/lib/types';
import { countryFlag, formatNumber, formatPercent, getCountryReelFarmCode } from '@/lib/utils';

export function TagBoard({
  products,
  selectedProductId,
  dashboard,
  loading,
  onProductChange,
  onRefresh
}: {
  products: Product[];
  selectedProductId: string;
  dashboard?: TagDashboard | null;
  loading: boolean;
  onProductChange: (productId: string) => void;
  onRefresh: () => void;
}) {
  const selectedProduct = products.find(product => product.id === selectedProductId) || products[0];

  return (
    <section className="tag-board">
      <div className="tag-board-hero">
        <div>
          <h2>Tag 看板</h2>
          <p>每个产品单独管理 Tag，把同一产品下不同国家的账号聚拢起来观察。</p>
        </div>
        <div className="tag-board-controls">
          <select className="text-input" value={selectedProduct?.id || ''} onChange={event => onProductChange(event.target.value)}>
            {products.map(product => <option value={product.id} key={product.id}>{product.name}</option>)}
          </select>
          <button className="btn ghost" type="button" onClick={onRefresh} disabled={loading}>{loading ? '读取中...' : '刷新'}</button>
        </div>
      </div>

      <div className="tag-grid">
        {dashboard?.tags?.length ? dashboard.tags.map(tag => (
          <article className="tag-card" key={tag.tag}>
            <div className="tag-card-head">
              <div>
                <span className="tag-name">#{tag.tag}</span>
                <p>{tag.account_count} 个账号</p>
              </div>
            </div>
            <div className="tag-kpis">
              <div><span>昨日均播</span><strong>{formatNumber(tag.yesterday_avg_views)}</strong></div>
              <div><span>7日均播</span><strong>{formatNumber(tag.seven_day_avg_views)}</strong></div>
              <div><span>7日 ER</span><strong>{formatPercent(tag.seven_day_er)}</strong></div>
            </div>
            <div className="tag-country-list">
              {tag.countries.map(country => (
                <section className="tag-country-group" key={country.country_id || country.country_code}>
                  <h3>{countryFlag({ id: country.country_id || '', name: country.country_name || '', reelFarmCode: country.country_code || getCountryReelFarmCode({ id: '', name: country.country_name || '' }) })} {country.country_name || country.country_code}</h3>
                  <div className="tag-account-list">
                    {country.accounts.map(account => (
                      <div className="tag-account-row" key={account.account_id}>
                        <span className="tag-account-avatar">{account.avatar_url ? <img src={account.avatar_url} alt="" /> : (account.username || '?').slice(0, 2).toUpperCase()}</span>
                        <div>
                          <strong>@{String(account.username || account.display_name || account.account_id).replace(/^@/, '')}</strong>
                          <span>{formatNumber(account.post_count || 0)} posts · {formatNumber(account.total_views || 0)} views</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </article>
        )) : <div className="empty-state">这个产品还没有 Tag。先在账号卡片里点击「+ Tag」添加。</div>}
      </div>
    </section>
  );
}
