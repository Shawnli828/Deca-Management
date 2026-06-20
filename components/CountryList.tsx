'use client';

import { useAccountPool } from '@/hooks/useAccountPool';
import type { Country, Product, ProductKpis } from '@/lib/types';
import { countryFlag, formatNumber, getCountryReelFarmCode } from '@/lib/utils';
import { AccountPoolTable } from './AccountPoolTable';
import { AccountTagEditorModal, CategoryTagFilter } from './CountryAccountTags';
import { DateRangeFilter } from './DateRangeFilter';

export function CountryList({
  product,
  kpis,
  dataSource = 'reelfarm',
  syncing,
  onBack,
  onSelect,
  onOpenSettings,
  onSyncProduct
}: {
  product: Product;
  kpis?: ProductKpis | null;
  dataSource?: 'reelfarm' | 'museon_clone';
  syncing?: boolean;
  onBack: () => void;
  onSelect: (country: Country) => void;
  onOpenSettings: () => void;
  onSyncProduct: (product: Product) => void | Promise<void>;
}) {
  const countries = product.countries || [];
  const accountPool = useAccountPool({ product, countries, dataSource, onSyncProduct });

  return (
    <section className="page active">
      <nav className="breadcrumbs">
        <button className="crumb-btn" onClick={onBack}>产品总览</button>
        <span>/</span>
        <strong>{product.name}</strong>
      </nav>
      <div className="account-pool-head">
        <div>
          <h2>Pool Accounts <span>{accountPool.filteredRows.length}</span></h2>
          <p>{product.name} 下所有国家/地区的 {dataSource === 'museon_clone' ? 'Clone Slide Show 账号池。' : 'TikTok 账号池。'}</p>
        </div>
        <div className="account-pool-actions">
          <button className="btn primary" type="button" onClick={accountPool.handleSyncProduct} disabled={syncing || !countries.length}>
            {syncing ? '同步中...' : dataSource === 'museon_clone' ? '同步 Clone 产品' : '同步当前产品'}
          </button>
          <button className="btn ghost" type="button" onClick={accountPool.loadAccountPool} disabled={accountPool.loading}>{accountPool.loading ? 'Refreshing...' : 'Refresh'}</button>
          <button className="btn ghost country-code-settings-btn" type="button" onClick={onOpenSettings}>
            国家/地区与 Code
          </button>
        </div>
      </div>

      <div className="account-pool-filters">
        <input className="text-input" value={accountPool.search} onChange={event => accountPool.setSearch(event.target.value)} placeholder="Search username..." />
        <select className="text-input" value={accountPool.countryFilter} onChange={event => accountPool.setCountryFilter(event.target.value)}>
          <option value="all">All Countries</option>
          {countries.map(country => <option value={getCountryReelFarmCode(country)} key={country.id}>{countryFlag(country)} {country.name}</option>)}
        </select>
        <select className="text-input" value={accountPool.statusFilter} onChange={event => accountPool.setStatusFilter(event.target.value)}>
          <option value="all">All Statuses</option>
          {accountPool.statusOptions.map(status => <option value={status} key={status}>{status}</option>)}
        </select>
        <select className="text-input" value={accountPool.publishMethodFilter} onChange={event => accountPool.setPublishMethodFilter(event.target.value)}>
          <option value="all">All Publish Methods</option>
          <option value="manual">manual</option>
          <option value="api">api</option>
          <option value="rpa">rpa</option>
        </select>
        <CategoryTagFilter tagOptions={accountPool.tagOptions} filters={accountPool.tagFilters} onApply={accountPool.setTagFilters} />
        <DateRangeFilter
          dateFrom={accountPool.dateFrom}
          dateTo={accountPool.dateTo}
          onApply={(from, to) => {
            accountPool.setDateFrom(from);
            accountPool.setDateTo(to);
          }}
        />
      </div>

      <div className="account-level-row">
        <span><i className="dot healthy" /> Accounts: {formatNumber(accountPool.rows.length)}</span>
        <span><i className="dot usable" /> Countries: {formatNumber(countries.length)}</span>
        <span><i className="dot star" /> Filtered: {formatNumber(accountPool.filteredRows.length)}</span>
      </div>
      {accountPool.error ? (
        <div className="account-pool-error">{accountPool.error}</div>
      ) : null}

      <section className="pool-performance">
        <div className="pool-performance-head">
          <div>
            <strong>Performance Dashboard</strong>
            <span>Aggregated across all accounts matching the current filters.</span>
          </div>
          <span>Filter-aware</span>
        </div>
        <div className="pool-performance-grid">
          {accountPool.performanceMetrics.map(metric => (
            <div className="pool-performance-card" key={metric.label}>
              <div className="pool-performance-label">
                <span>{metric.label}</span>
                {metric.note ? <b title={metric.note}>i</b> : null}
              </div>
              <strong>{metric.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <AccountPoolTable
        rows={accountPool.sortedRows}
        loading={accountPool.loading}
        viewSort={accountPool.viewSort}
        dataSource={dataSource}
        expandedAccounts={accountPool.expandedAccounts}
        postCache={accountPool.postCache}
        accountRowKey={accountPool.accountRowKey}
        onToggleViewSort={accountPool.toggleViewSort}
        onToggleAccount={accountPool.toggleAccount}
        onPagePosts={accountPool.loadAccountPosts}
        onRemoveTag={accountPool.removeAccountTag}
        onEditTags={accountPool.setEditingTagAccountId}
      />
      {accountPool.editingTagRow ? (
        <AccountTagEditorModal
          row={accountPool.editingTagRow}
          availableTags={accountPool.tagOptions}
          onClose={() => accountPool.setEditingTagAccountId('')}
          onAddTag={accountPool.addAccountTag}
          onRemoveTag={accountPool.removeAccountTag}
          onDeleteProductTag={accountPool.deleteProductTagOption}
        />
      ) : null}
    </section>
  );
}
