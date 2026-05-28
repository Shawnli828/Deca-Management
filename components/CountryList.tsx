'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { AccountSummary, Country, Product, ProductKpis } from '@/lib/types';
import { countryFlag, formatNumber, formatUtcReadable, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

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
  const [rows, setRows] = useState<Array<AccountSummary & { country: Country; tags?: string[] }>>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [countryFilter, setCountryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tagFilter, setTagFilter] = useState('all');

  async function loadAccountPool() {
    if (!product) return;
    setLoading(true);
    try {
      const productCode = getProductReelFarmCode(product);
      const chunks = await Promise.all(countries.map(async country => {
        const params = new URLSearchParams({
          resource: 'accounts',
          product_code: productCode,
          country_code: getCountryReelFarmCode(country)
        });
        const payload = await api.dataQuery<{ ok: boolean; data: AccountSummary[] }>(params);
        return (payload.data || []).map(account => ({ ...account, country }));
      }));
      const accounts = chunks.flat();
      const accountIds = accounts.map(account => account.account_id).filter(Boolean);
      const tagMap: Record<string, string[]> = {};
      for (let index = 0; index < accountIds.length; index += 80) {
        const tagPayload = await api.accountTags(accountIds.slice(index, index + 80));
        Object.assign(tagMap, tagPayload.tags || {});
      }
      setRows(accounts.map(account => ({ ...account, tags: tagMap[account.account_id] || [] })));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAccountPool().catch(() => setLoading(false));
  }, [product.id]);

  const tagOptions = useMemo(() => {
    return Array.from(new Set(rows.flatMap(row => row.tags || []))).sort((a, b) => a.localeCompare(b));
  }, [rows]);

  const filteredRows = rows.filter(row => {
    const query = search.trim().toLowerCase();
    const username = String(row.username || row.display_name || row.account_id || '').toLowerCase();
    const countryCode = getCountryReelFarmCode(row.country);
    const status = String(row.status || 'unknown').toLowerCase();
    if (query && !username.includes(query)) return false;
    if (countryFilter !== 'all' && countryCode !== countryFilter) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    if (tagFilter !== 'all' && !(row.tags || []).includes(tagFilter)) return false;
    return true;
  });

  const statusOptions = Array.from(new Set(rows.map(row => String(row.status || 'unknown').toLowerCase()))).sort();

  return (
    <section className="page active">
      <nav className="breadcrumbs">
        <button className="crumb-btn" onClick={onBack}>产品总览</button>
        <span>/</span>
        <strong>{product.name}</strong>
      </nav>
      <div className="account-pool-head">
        <div>
          <h2>Pool Accounts <span>{filteredRows.length}</span></h2>
          <p>{product.name} 下所有国家/地区的 TikTok 账号池。</p>
        </div>
        <div className="account-pool-actions">
          <button className="btn ghost" type="button" onClick={loadAccountPool} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
          <button className="product-settings-btn inline" type="button" onClick={onOpenSettings} title="国家/地区设置" aria-label="国家/地区设置">⚙</button>
        </div>
      </div>

      <div className="account-pool-filters">
        <input className="text-input" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search username..." />
        <select className="text-input" value={countryFilter} onChange={event => setCountryFilter(event.target.value)}>
          <option value="all">All Countries</option>
          {countries.map(country => <option value={getCountryReelFarmCode(country)} key={country.id}>{countryFlag(country)} {country.name}</option>)}
        </select>
        <select className="text-input" value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>
          <option value="all">All Statuses</option>
          {statusOptions.map(status => <option value={status} key={status}>{status}</option>)}
        </select>
        <select className="text-input" value={tagFilter} onChange={event => setTagFilter(event.target.value)}>
          <option value="all">Tags</option>
          {tagOptions.map(tag => <option value={tag} key={tag}>{tag}</option>)}
        </select>
      </div>

      <div className="account-level-row">
        <span><i className="dot healthy" /> Accounts: {formatNumber(rows.length)}</span>
        <span><i className="dot usable" /> Countries: {formatNumber(countries.length)}</span>
        <span><i className="dot star" /> Filtered: {formatNumber(filteredRows.length)}</span>
      </div>

      <section className="pool-performance">
        <div>
          <strong>Performance Dashboard</strong>
          <span>Aggregated across all accounts matching the current filters.</span>
        </div>
        <span>Filter-aware</span>
      </section>

      <div className="account-pool-table-wrap">
        <table className="account-pool-table">
          <thead>
            <tr>
              <th><input type="checkbox" aria-label="Select all accounts" /></th>
              <th>Account</th>
              <th>Avg Views</th>
              <th>Country</th>
              <th>Status</th>
              <th>Posts</th>
              <th>Tags</th>
              <th>Synced</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} className="pool-empty">Loading accounts...</td></tr>
            ) : filteredRows.length ? filteredRows.map(row => {
              const avgViews = row.post_count ? Math.round((Number(row.total_views) || 0) / Number(row.post_count)) : 0;
              return (
                <tr key={`${row.country.id}:${row.account_id}`}>
                  <td><input type="checkbox" aria-label={`Select ${row.username || row.account_id}`} /></td>
                  <td>
                    <div className="pool-account-cell">
                      <span className="pool-avatar">{row.avatar_url ? <img src={row.avatar_url} alt="" /> : (row.username || '?').slice(0, 2).toUpperCase()}</span>
                      <span>
                        <strong>{row.display_name || row.username || 'Unknown'}</strong>
                        <small>@{String(row.username || row.account_id).replace(/^@/, '')}</small>
                      </span>
                    </div>
                  </td>
                  <td>{avgViews ? formatNumber(avgViews) : '—'}</td>
                  <td>{countryFlag(row.country)} {row.country.name}</td>
                  <td><span className="pool-pill">{row.status || 'N/A'}</span></td>
                  <td>{formatNumber(row.post_count || 0)}</td>
                  <td>
                    <div className="pool-tags">
                      {(row.tags || []).slice(0, 2).map(tag => <span key={tag}>{tag.replace(/^Creative:\s*/, '')}</span>)}
                      {!(row.tags || []).length ? '—' : null}
                    </div>
                  </td>
                  <td>{row.last_synced_at ? formatUtcReadable(row.last_synced_at) : '—'}</td>
                  <td><button className="pool-detail-btn" type="button" onClick={() => onSelect(row.country)}>Details</button></td>
                </tr>
              );
            }) : (
              <tr><td colSpan={9} className="pool-empty">No accounts match the current filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
