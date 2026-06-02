'use client';

import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '@/lib/api';
import type { AccountSummary, Country, DetailedPostRow, Product, ProductKpis } from '@/lib/types';
import { countryFlag, formatNumber, formatUtcReadable, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';
import { composeTag, formatTagLabel, getTagCategory, getTagName } from './ReelFarmAccountCard';

type AccountPoolRow = AccountSummary & { country: Country; tags?: string[] };
type AccountPostState = {
  rows: DetailedPostRow[];
  loading: boolean;
  error: string;
  offset: number;
  hasMore: boolean;
  total?: number;
};
type TagFilterRow = { id: string; category: string; tags: string[] };
type ViewSortDirection = 'none' | 'desc' | 'asc';

const ACCOUNT_POST_PAGE_SIZE = 4;
const DATE_PRESETS = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
  { key: '3m', label: 'Last 3 months' },
  { key: '6m', label: 'Last 6 months' }
] as const;

type DatePresetKey = typeof DATE_PRESETS[number]['key'];

function dateInputValue(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function parseInputDate(value: string) {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function addMonths(date: Date, months: number) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

function rangeForPreset(preset: DatePresetKey) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (preset === 'today') return { from: dateInputValue(today), to: dateInputValue(today) };
  if (preset === 'yesterday') {
    const yesterday = addDays(today, -1);
    return { from: dateInputValue(yesterday), to: dateInputValue(yesterday) };
  }
  if (preset === '30d') return { from: dateInputValue(addDays(today, -29)), to: dateInputValue(today) };
  if (preset === '3m') return { from: dateInputValue(addMonths(today, -3)), to: dateInputValue(today) };
  if (preset === '6m') return { from: dateInputValue(addMonths(today, -6)), to: dateInputValue(today) };
  return { from: dateInputValue(addDays(today, -6)), to: dateInputValue(today) };
}

function displayDateRange(from: string, to: string) {
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  return `${formatter.format(parseInputDate(from))} - ${formatter.format(parseInputDate(to))}`;
}

function sameDate(left: string, right: string) {
  return left === right;
}

const defaultDateRange = rangeForPreset('7d');

function getAccountAvgViews(row: AccountPoolRow) {
  const posts = Number(row.post_count) || 0;
  if (!posts) return 0;
  return Math.round((Number(row.total_views) || 0) / posts);
}

function getAutomationDisplay(row: AccountPoolRow, dataSource: 'reelfarm' | 'museon_clone') {
  const names = String(row.automation_names || row.automation_name || '').trim();
  if (names) return names;
  return dataSource === 'museon_clone' ? 'api' : 'rpa';
}

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
  const [rows, setRows] = useState<AccountPoolRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [countryFilter, setCountryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tagFilters, setTagFilters] = useState<TagFilterRow[]>([]);
  const [dateFrom, setDateFrom] = useState(defaultDateRange.from);
  const [dateTo, setDateTo] = useState(defaultDateRange.to);
  const [viewSort, setViewSort] = useState<ViewSortDirection>('none');
  const [expandedAccounts, setExpandedAccounts] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, AccountPostState>>({});
  const [editingTagAccountId, setEditingTagAccountId] = useState('');
  const [productTagOptions, setProductTagOptions] = useState<string[]>([]);

  function addDateFilters(params: URLSearchParams) {
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    return params;
  }

  async function loadAccountPool() {
    if (!product) return;
    setLoading(true);
    try {
      const productCode = getProductReelFarmCode(product);
      const productTagsRequest = api.productTags(productCode).catch(() => ({ ok: false, product_code: productCode, tags: [] as string[] }));
      const accountsRequest = Promise.all(countries.map(async country => {
        const params = addDateFilters(new URLSearchParams({
          resource: 'accounts',
          product_code: productCode,
          country_code: getCountryReelFarmCode(country)
        }));
        if (dataSource !== 'reelfarm') params.set('source', dataSource);
        const payload = await api.dataQuery<{ ok: boolean; data: AccountSummary[] }>(params);
        return (payload.data || []).map(account => ({ ...account, country }));
      }));
      const [chunks, productTagsPayload] = await Promise.all([accountsRequest, productTagsRequest]);
      setProductTagOptions(productTagsPayload.tags || []);
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

  async function handleSyncProduct() {
    await onSyncProduct(product);
    await loadAccountPool();
  }

  useEffect(() => {
    loadAccountPool().catch(() => setLoading(false));
  }, [product.id, dataSource, dateFrom, dateTo]);

  useEffect(() => {
    setExpandedAccounts({});
    setPostCache({});
  }, [product.id, dataSource, dateFrom, dateTo]);

  function accountRowKey(row: AccountPoolRow) {
    return `${row.country.id}:${row.account_id}:${dateFrom || 'start'}:${dateTo || 'end'}`;
  }

  async function loadAccountPosts(row: AccountPoolRow, offset = 0) {
    const key = accountRowKey(row);
    const cached = postCache[key];
    if (cached && cached.offset === offset && cached.rows.length && !cached.error) return;

    setPostCache(previous => ({
      ...previous,
      [key]: {
        rows: previous[key]?.rows || [],
        offset,
        hasMore: previous[key]?.hasMore || false,
        total: previous[key]?.total,
        loading: true,
        error: ''
      }
    }));

    try {
      const params = addDateFilters(new URLSearchParams({
        resource: 'account_posts',
        product_code: getProductReelFarmCode(product),
        country_code: getCountryReelFarmCode(row.country),
        account_id: row.account_id,
        limit: String(ACCOUNT_POST_PAGE_SIZE),
        offset: String(offset)
      }));
      if (dataSource !== 'reelfarm') params.set('source', dataSource);
      const payload = await api.dataQuery<{
        ok: boolean;
        data: DetailedPostRow[];
        pagination?: { limit: number; offset: number; has_more: boolean; total?: number };
      }>(params);
      setPostCache(previous => ({
        ...previous,
        [key]: {
          rows: payload.data || [],
          offset,
          hasMore: Boolean(payload.pagination?.has_more),
          total: payload.pagination?.total,
          loading: false,
          error: ''
        }
      }));
    } catch (error: any) {
      setPostCache(previous => ({
        ...previous,
        [key]: {
          rows: previous[key]?.rows || [],
          offset,
          hasMore: false,
          total: previous[key]?.total,
          loading: false,
          error: error?.message || 'Posts loading failed.'
        }
      }));
    }
  }

  function toggleAccount(row: AccountPoolRow) {
    const key = accountRowKey(row);
    setExpandedAccounts(previous => ({ ...previous, [key]: !previous[key] }));
    if (!expandedAccounts[key]) {
      loadAccountPosts(row, postCache[key]?.offset || 0);
    }
  }

  const tagOptions = useMemo(() => {
    return Array.from(new Set([
      ...productTagOptions,
      ...rows.flatMap(row => row.tags || [])
    ])).filter(Boolean).sort((a, b) => a.localeCompare(b));
  }, [productTagOptions, rows]);
  const editingTagRow = editingTagAccountId ? rows.find(row => row.account_id === editingTagAccountId) : null;

  async function addAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    const nextTag = tag.trim();
    if (!accountId || !nextTag) return;
    const productTagsPayload = await api.createProductTag(getProductReelFarmCode(product), nextTag);
    setProductTagOptions(productTagsPayload.tags || []);
    const payload = await api.addAccountTag(accountId, nextTag);
    setRows(previous => previous.map(item => item.account_id === accountId
      ? { ...item, tags: Array.from(new Set([...(item.tags || []), payload.tag])) }
      : item
    ));
  }

  async function removeAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    if (!accountId || !tag) return;
    await api.deleteAccountTag(accountId, tag);
    setRows(previous => previous.map(item => item.account_id === accountId
      ? { ...item, tags: (item.tags || []).filter(value => value !== tag) }
      : item
    ));
  }

  function matchesTagFilters(row: AccountPoolRow) {
    const activeFilters = tagFilters.filter(filter => filter.category && filter.tags.length);
    if (!activeFilters.length) return true;
    const rowTags = row.tags || [];
    return activeFilters.every(filter => {
      const selected = new Set(filter.tags);
      return rowTags.some(tag => getTagCategory(tag) === filter.category && selected.has(tag));
    });
  }

  const filteredRows = rows.filter(row => {
    const query = search.trim().toLowerCase();
    const username = String(row.username || row.display_name || row.account_id || '').toLowerCase();
    const countryCode = getCountryReelFarmCode(row.country);
    const status = String(row.status || 'unknown').toLowerCase();
    if (query && !username.includes(query)) return false;
    if (countryFilter !== 'all' && countryCode !== countryFilter) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    if (!matchesTagFilters(row)) return false;
    return true;
  });
  const sortedRows = useMemo(() => {
    if (viewSort === 'none') return filteredRows;
    return [...filteredRows].sort((left, right) => {
      const leftViews = getAccountAvgViews(left);
      const rightViews = getAccountAvgViews(right);
      if (leftViews === rightViews) {
        return String(left.username || left.display_name || left.account_id || '')
          .localeCompare(String(right.username || right.display_name || right.account_id || ''));
      }
      return viewSort === 'desc' ? rightViews - leftViews : leftViews - rightViews;
    });
  }, [filteredRows, viewSort]);

  function toggleViewSort() {
    setViewSort(previous => previous === 'desc' ? 'asc' : 'desc');
  }

  const statusOptions = Array.from(new Set(rows.map(row => String(row.status || 'unknown').toLowerCase()))).sort();
  const performanceMetrics = useMemo(() => {
    const accountCount = filteredRows.length;
    const postedCount = filteredRows.filter(row => Number(row.post_count) > 0).length;
    const posts = filteredRows.reduce((sum, row) => sum + (Number(row.post_count) || 0), 0);
    const views = filteredRows.reduce((sum, row) => sum + (Number(row.total_views) || 0), 0);
    const likes = filteredRows.reduce((sum, row) => sum + (Number(row.total_likes) || 0), 0);
    const comments = filteredRows.reduce((sum, row) => sum + (Number(row.total_comments) || 0), 0);
    const shares = filteredRows.reduce((sum, row) => sum + (Number(row.total_shares) || 0), 0);
    const avgViews = posts ? Math.round(views / posts) : 0;
    const engagement = views ? ((likes + comments + shares) / views) * 100 : 0;

    return [
      { label: 'POSTED', value: `${formatNumber(postedCount)}/${formatNumber(accountCount)}`, note: 'Accounts with posts / filtered accounts' },
      { label: 'POSTS', value: formatNumber(posts) },
      { label: 'VIEWS', value: formatNumber(views) },
      { label: 'AVG VIEWS', value: formatNumber(avgViews), note: 'Filtered total views / filtered posts' },
      { label: 'LIKES', value: formatNumber(likes) },
      { label: 'COMMENTS', value: formatNumber(comments) },
      { label: 'SHARES', value: formatNumber(shares) },
      { label: 'ENGAGEMENT', value: `${engagement.toFixed(2)}%`, note: '(Likes + comments + shares) / views' }
    ];
  }, [filteredRows]);

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
          <p>{product.name} 下所有国家/地区的 {dataSource === 'museon_clone' ? 'Clone Slide Show 账号池。' : 'TikTok 账号池。'}</p>
        </div>
        <div className="account-pool-actions">
          <button className="btn primary" type="button" onClick={handleSyncProduct} disabled={syncing || !countries.length}>
            {syncing ? '同步中...' : dataSource === 'museon_clone' ? '同步 Clone 产品' : '同步当前产品'}
          </button>
          <button className="btn ghost" type="button" onClick={loadAccountPool} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
          <button className="btn ghost country-code-settings-btn" type="button" onClick={onOpenSettings}>
            国家/地区与 Code
          </button>
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
        <CategoryTagFilter tagOptions={tagOptions} filters={tagFilters} onApply={setTagFilters} />
        <DateRangeFilter
          dateFrom={dateFrom}
          dateTo={dateTo}
          onApply={(from, to) => {
            setDateFrom(from);
            setDateTo(to);
          }}
        />
      </div>

      <div className="account-level-row">
        <span><i className="dot healthy" /> Accounts: {formatNumber(rows.length)}</span>
        <span><i className="dot usable" /> Countries: {formatNumber(countries.length)}</span>
        <span><i className="dot star" /> Filtered: {formatNumber(filteredRows.length)}</span>
      </div>

      <section className="pool-performance">
        <div className="pool-performance-head">
          <div>
            <strong>Performance Dashboard</strong>
            <span>Aggregated across all accounts matching the current filters.</span>
          </div>
          <span>Filter-aware</span>
        </div>
        <div className="pool-performance-grid">
          {performanceMetrics.map(metric => (
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

      <div className="account-pool-table-wrap">
        <table className="account-pool-table">
          <thead>
            <tr>
              <th><input type="checkbox" aria-label="Select all accounts" /></th>
              <th>Account</th>
              <th>
                <button className="pool-sort-head" type="button" onClick={toggleViewSort} aria-label="Sort by average views">
                  Avg Views <span>{viewSort === 'asc' ? '↑' : viewSort === 'desc' ? '↓' : '↕'}</span>
                </button>
              </th>
              <th>Automation</th>
              <th>Country</th>
              <th>Status</th>
              <th>Posts</th>
              <th>Tags</th>
              <th>Synced</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} className="pool-empty">Loading accounts...</td></tr>
            ) : sortedRows.length ? sortedRows.map(row => {
              const avgViews = getAccountAvgViews(row);
              const rowKey = accountRowKey(row);
              const isExpanded = Boolean(expandedAccounts[rowKey]);
              const automationDisplay = getAutomationDisplay(row, dataSource);
              return (
                <Fragment key={rowKey}>
                  <tr key={rowKey}>
                    <td><input type="checkbox" aria-label={`Select ${row.username || row.account_id}`} /></td>
                    <td>
                      <div className="pool-account-cell">
                        <button
                          className={isExpanded ? 'pool-expand-btn open' : 'pool-expand-btn'}
                          type="button"
                          onClick={() => toggleAccount(row)}
                          aria-label={isExpanded ? 'Close posts' : 'Open posts'}
                          aria-expanded={isExpanded}
                        />
                        <span className="pool-avatar">{row.avatar_url ? <img src={row.avatar_url} alt="" /> : (row.username || '?').slice(0, 2).toUpperCase()}</span>
                        <span>
                          <strong>{row.display_name || row.username || 'Unknown'}</strong>
                          <small>@{String(row.username || row.account_id).replace(/^@/, '')}</small>
                        </span>
                      </div>
                    </td>
                    <td>{avgViews ? formatNumber(avgViews) : '—'}</td>
                    <td>
                      <span className="pool-automation-list" title={automationDisplay}>{automationDisplay}</span>
                    </td>
                    <td>{countryFlag(row.country)} {row.country.name}</td>
                    <td><span className="pool-pill">{row.status || 'N/A'}</span></td>
                    <td>{formatNumber(row.post_count || 0)}</td>
                    <td>
                      <div className="pool-tags">
                        {(row.tags || []).map(tag => (
                          <button
                            className="pool-tag-chip"
                            style={accountTagStyle(tag)}
                            type="button"
                            key={tag}
                            onClick={() => removeAccountTag(row, tag)}
                            title="点击删除这个 Tag"
                          >
                            {formatTagLabel(tag)} <span>×</span>
                          </button>
                        ))}
                        <button className="pool-tag-add" type="button" onClick={() => setEditingTagAccountId(row.account_id)} title="添加 Tag">+</button>
                      </div>
                    </td>
                    <td>{row.last_synced_at ? formatUtcReadable(row.last_synced_at) : '—'}</td>
                  </tr>
                  {isExpanded ? (
                    <tr className="account-posts-row" key={`${rowKey}:posts`}>
                      <td colSpan={9}>
                        <AccountPostPanel
                          row={row}
                          state={postCache[rowKey]}
                          onPage={offset => loadAccountPosts(row, offset)}
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            }) : (
              <tr><td colSpan={9} className="pool-empty">No accounts match the current filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {editingTagRow ? (
        <AccountTagEditorModal
          row={editingTagRow}
          availableTags={tagOptions}
          onClose={() => setEditingTagAccountId('')}
          onAddTag={addAccountTag}
          onRemoveTag={removeAccountTag}
        />
      ) : null}
    </section>
  );
}

function CategoryTagFilter({
  tagOptions,
  filters,
  onApply
}: {
  tagOptions: string[];
  filters: TagFilterRow[];
  onApply: (filters: TagFilterRow[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<TagFilterRow[]>(filters);
  const containerRef = useRef<HTMLDivElement>(null);
  const categories = useMemo(() => Array.from(new Set(tagOptions.map(getTagCategory))).filter(Boolean).sort(), [tagOptions]);

  function openFilter() {
    if (open) {
      setOpen(false);
      return;
    }
    setDraft(filters.length ? filters : [{ id: generateUiId(), category: categories[0] || '', tags: [] }]);
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (target instanceof Node && containerRef.current?.contains(target)) return;
      setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  function tagsForCategory(category: string) {
    return tagOptions.filter(tag => getTagCategory(tag) === category);
  }

  function updateRow(id: string, updater: (row: TagFilterRow) => TagFilterRow) {
    setDraft(previous => previous.map(row => row.id === id ? updater(row) : row));
  }

  const complete = draft.filter(row => row.category && row.tags.length);
  const canApply = complete.length === draft.length && draft.length > 0;
  const summary = filters.length
    ? `${filters.length} Tag Filter${filters.length > 1 ? 's' : ''}`
    : 'Tags';

  return (
    <div className="category-tag-filter" ref={containerRef}>
      <button className="text-input tag-filter-trigger" type="button" onClick={openFilter}>
        <span>{summary}</span>
        <span>⌄</span>
      </button>
      {open ? (
        <div className="tag-filter-popover">
          <div className="tag-filter-head">
            <div>
              <strong>Category + Tags</strong>
              <span>One category per row. Tags in that row are multi-select.</span>
            </div>
            <button type="button" onClick={() => setDraft(previous => [...previous, { id: generateUiId(), category: categories[0] || '', tags: [] }])}>+ Add</button>
          </div>
          <div className="tag-filter-rows">
            {draft.map(row => {
              const options = tagsForCategory(row.category);
              return (
                <div className="tag-filter-row" key={row.id}>
                  <select
                    value={row.category}
                    onChange={event => updateRow(row.id, () => ({ ...row, category: event.target.value, tags: [] }))}
                  >
                    <option value="">Category</option>
                    {categories.map(category => <option value={category} key={category}>{category}</option>)}
                  </select>
                  <div className="tag-filter-tagbox">
                    <button className="tag-filter-tagbox-summary" type="button">
                      <span>{row.tags.length ? `${row.tags.length} selected` : 'Select tags'}</span>
                      <b>{row.tags.length}</b>
                      <span>⌄</span>
                    </button>
                    <div className="tag-filter-options">
                      {options.length ? options.map(tag => {
                        const checked = row.tags.includes(tag);
                        return (
                          <label key={tag}>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => updateRow(row.id, current => ({
                                ...current,
                                tags: checked ? current.tags.filter(item => item !== tag) : [...current.tags, tag]
                              }))}
                            />
                            <span style={accountTagStyle(tag)}>{getTagName(tag)}</span>
                          </label>
                        );
                      }) : <em>Select a category first</em>}
                    </div>
                  </div>
                  <button className="tag-filter-remove" type="button" onClick={() => setDraft(previous => previous.filter(item => item.id !== row.id))}>×</button>
                </div>
              );
            })}
          </div>
          <div className="tag-filter-actions">
            <button type="button" onClick={() => { onApply([]); setDraft([]); }}>Clear All</button>
            <span>{canApply ? 'Ready to apply filters.' : 'Select at least one tag for each selected category.'}</span>
            <button
              className="primary"
              type="button"
              disabled={!canApply}
              onClick={() => {
                onApply(complete);
                setOpen(false);
              }}
            >
              Apply Filters
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AccountTagEditorModal({
  row,
  availableTags,
  onClose,
  onAddTag,
  onRemoveTag
}: {
  row: AccountPoolRow;
  availableTags: string[];
  onClose: () => void;
  onAddTag: (row: AccountPoolRow, tag: string) => void;
  onRemoveTag: (row: AccountPoolRow, tag: string) => void;
}) {
  const [mounted, setMounted] = useState(false);
  const [categoryInput, setCategoryInput] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [categoryMenuOpen, setCategoryMenuOpen] = useState(false);
  const [tagMenuOpen, setTagMenuOpen] = useState(false);
  const categoryMenuRef = useRef<HTMLDivElement>(null);
  const tagMenuRef = useRef<HTMLDivElement>(null);
  const tags = row.tags || [];
  const categories = Array.from(new Set(availableTags.map(getTagCategory).filter(Boolean))).sort((a, b) => a.localeCompare(b));
  const normalizedCategory = categoryInput.trim().toLowerCase();
  const tagOptions = availableTags.filter(tag => !normalizedCategory || getTagCategory(tag).toLowerCase() === normalizedCategory);
  const categorySuggestions = categories.filter(category => !normalizedCategory || category.toLowerCase().includes(normalizedCategory));
  const normalizedTag = tagInput.trim().toLowerCase();
  const tagSuggestions = Array.from(new Set(tagOptions.map(getTagName)))
    .filter(tag => !normalizedTag || tag.toLowerCase().includes(normalizedTag))
    .sort((a, b) => a.localeCompare(b));
  const canAddTag = Boolean(categoryInput.trim() && tagInput.trim());

  function commitTag() {
    if (!canAddTag) return;
    onAddTag(row, composeTag(categoryInput, tagInput));
    setTagInput('');
    setTagMenuOpen(false);
  }

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!categoryMenuRef.current?.contains(target)) setCategoryMenuOpen(false);
      if (!tagMenuRef.current?.contains(target)) setTagMenuOpen(false);
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <div className="tag-editor-backdrop" onClick={onClose}>
      <div className="tag-editor-modal" onClick={event => event.stopPropagation()}>
        <button className="tag-editor-close" type="button" onClick={onClose}>×</button>
        <h3>Edit Creator Tags</h3>
        <div className="tag-editor-current">
          {tags.length ? tags.map(tag => (
            <button className="creator-tag-chip" style={accountTagStyle(tag)} type="button" key={tag} onClick={() => onRemoveTag(row, tag)}>
              {formatTagLabel(tag)} ×
            </button>
          )) : <span className="creator-tag-empty">No tags yet</span>}
        </div>
        <div className="tag-editor-section-title">Add Tag</div>
        <div className="tag-editor-row">
          <div className="tag-editor-combobox" ref={categoryMenuRef}>
            <div className="tag-editor-field">
              <span>⌕</span>
              <input
                value={categoryInput}
                onFocus={() => setCategoryMenuOpen(true)}
                onChange={event => {
                  setCategoryInput(event.target.value);
                  setTagInput('');
                  setCategoryMenuOpen(true);
                }}
                placeholder="Select or type category"
                autoComplete="off"
              />
              <button
                className="tag-editor-menu-toggle"
                type="button"
                aria-label="选择 Category"
                onClick={() => setCategoryMenuOpen(previous => !previous)}
              >
                ⌄
              </button>
            </div>
            {categoryMenuOpen ? (
              <div className="tag-editor-list">
                {categorySuggestions.length ? categorySuggestions.map(category => (
                  <button
                    type="button"
                    key={category}
                    onClick={() => {
                      setCategoryInput(category);
                      setTagInput('');
                      setCategoryMenuOpen(false);
                      setTagMenuOpen(true);
                    }}
                  >
                    {category}
                  </button>
                )) : <span className="tag-editor-list-empty">No existing category. Type to create new.</span>}
              </div>
            ) : null}
          </div>
          <div className="tag-editor-combobox" ref={tagMenuRef}>
            <div className="tag-editor-field">
              <span>⌕</span>
              <input
                value={tagInput}
                onFocus={() => {
                  if (categoryInput.trim()) setTagMenuOpen(true);
                }}
                onChange={event => {
                  setTagInput(event.target.value);
                  setTagMenuOpen(Boolean(categoryInput.trim()));
                }}
                onKeyDown={event => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    commitTag();
                  }
                }}
                placeholder={categoryInput.trim() ? 'Select or type tag' : 'Select category first...'}
                autoComplete="off"
                disabled={!categoryInput.trim()}
              />
              <button
                className="tag-editor-menu-toggle"
                type="button"
                aria-label="选择 Tag"
                disabled={!categoryInput.trim()}
                onClick={() => setTagMenuOpen(previous => categoryInput.trim() ? !previous : false)}
              >
                ⌄
              </button>
            </div>
            {tagMenuOpen ? (
              <div className="tag-editor-list">
                {tagSuggestions.length ? tagSuggestions.map(tag => (
                  <button
                    type="button"
                    key={tag}
                    onClick={() => {
                      setTagInput(tag);
                      setTagMenuOpen(false);
                    }}
                  >
                    {tag}
                  </button>
                )) : <span className="tag-editor-list-empty">No existing tag. Type to create new.</span>}
              </div>
            ) : null}
          </div>
          <button
            className="tag-editor-add"
            type="button"
            disabled={!canAddTag}
            onClick={commitTag}
          >
            + Add
          </button>
        </div>
        <div className="tag-editor-actions">
          <button className="tag-editor-cancel" type="button" onClick={onClose}>Cancel</button>
          <button className="tag-editor-save" type="button" onClick={onClose}>Save Tags</button>
        </div>
      </div>
    </div>,
    document.body
  );
}

function generateUiId() {
  return Math.random().toString(36).slice(2, 10);
}

function accountTagStyle(value: string) {
  const palette = [
    { background: '#dbeafe', borderColor: '#93c5fd', color: '#1d4ed8' },
    { background: '#dcfce7', borderColor: '#86efac', color: '#15803d' },
    { background: '#fef3c7', borderColor: '#fbbf24', color: '#92400e' },
    { background: '#fce7f3', borderColor: '#f9a8d4', color: '#be185d' },
    { background: '#ede9fe', borderColor: '#c4b5fd', color: '#6d28d9' },
    { background: '#cffafe', borderColor: '#67e8f9', color: '#0e7490' }
  ];
  let hash = 0;
  for (const char of getTagCategory(value)) hash = char.charCodeAt(0) + ((hash << 5) - hash);
  const color = palette[Math.abs(hash) % palette.length];
  return color;
}

function DateRangeFilter({
  dateFrom,
  dateTo,
  onApply
}: {
  dateFrom: string;
  dateTo: string;
  onApply: (from: string, to: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(dateFrom);
  const [draftTo, setDraftTo] = useState(dateTo);
  const [month, setMonth] = useState(() => parseInputDate(dateFrom || defaultDateRange.from));

  function openPicker() {
    setDraftFrom(dateFrom);
    setDraftTo(dateTo);
    setMonth(parseInputDate(dateFrom || defaultDateRange.from));
    setOpen(true);
  }

  function applyPreset(preset: DatePresetKey) {
    const range = rangeForPreset(preset);
    setDraftFrom(range.from);
    setDraftTo(range.to);
    setMonth(parseInputDate(range.from));
  }

  function selectDay(value: string) {
    if (!draftFrom || (draftFrom && draftTo)) {
      setDraftFrom(value);
      setDraftTo('');
      return;
    }
    if (value < draftFrom) {
      setDraftTo(draftFrom);
      setDraftFrom(value);
      return;
    }
    setDraftTo(value);
  }

  const monthStart = new Date(month.getFullYear(), month.getMonth(), 1);
  const calendarStart = addDays(monthStart, -monthStart.getDay());
  const days = Array.from({ length: 42 }, (_, index) => addDays(calendarStart, index));
  const monthLabel = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(monthStart);

  return (
    <div className="date-range-filter">
      <button className="date-range-trigger" type="button" onClick={openPicker}>
        <span className="date-range-icon">▣</span>
        <span>{displayDateRange(dateFrom, dateTo)}</span>
      </button>
      {open ? (
        <div className="date-range-popover">
          <div className="date-range-presets">
            <h3>Date Range</h3>
            {DATE_PRESETS.map(preset => {
              const range = rangeForPreset(preset.key);
              const active = sameDate(draftFrom, range.from) && sameDate(draftTo, range.to);
              return (
                <button className={active ? 'active' : ''} type="button" key={preset.key} onClick={() => applyPreset(preset.key)}>
                  {preset.label}
                </button>
              );
            })}
          </div>
          <div className="date-calendar">
            <div className="date-calendar-head">
              <button type="button" onClick={() => setMonth(addMonths(month, -1))}>‹</button>
              <strong>{monthLabel}</strong>
              <button type="button" onClick={() => setMonth(addMonths(month, 1))}>›</button>
            </div>
            <div className="date-calendar-grid week">
              {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => <span key={day}>{day}</span>)}
            </div>
            <div className="date-calendar-grid">
              {days.map(day => {
                const value = dateInputValue(day);
                const outside = day.getMonth() !== month.getMonth();
                const selected = value === draftFrom || value === draftTo;
                const inRange = draftFrom && draftTo && value > draftFrom && value < draftTo;
                return (
                  <button
                    className={`${outside ? 'outside' : ''} ${selected ? 'selected' : ''} ${inRange ? 'in-range' : ''}`}
                    type="button"
                    key={value}
                    onClick={() => selectDay(value)}
                  >
                    {day.getDate()}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="date-range-actions">
            <button type="button" onClick={() => setOpen(false)}>Cancel</button>
            <button
              className="primary"
              type="button"
              onClick={() => {
                onApply(draftFrom || dateFrom, draftTo || draftFrom || dateTo);
                setOpen(false);
              }}
            >
              Apply
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AccountPostPanel({
  row,
  state,
  onPage
}: {
  row: AccountPoolRow;
  state?: AccountPostState;
  onPage: (offset: number) => void;
}) {
  const rows = state?.rows || [];
  const offset = state?.offset || 0;
  const currentPage = Math.floor(offset / ACCOUNT_POST_PAGE_SIZE) + 1;
  const totalPages = state?.total ? Math.max(1, Math.ceil(state.total / ACCOUNT_POST_PAGE_SIZE)) : undefined;
  const canGoNext = Boolean(state?.hasMore)
    || (rows.length === ACCOUNT_POST_PAGE_SIZE && (!state?.total || offset + rows.length < state.total));

  return (
    <div className="pool-post-panel">
      <div className="pool-post-panel-head">
        <div>
          <strong>Posts by @{String(row.username || row.account_id).replace(/^@/, '')}</strong>
          <span>{countryFlag(row.country)} {row.country.name}</span>
        </div>
        <div className="pool-post-pager">
          <button className="pool-detail-btn" type="button" disabled={state?.loading || offset <= 0} onClick={() => onPage(Math.max(0, offset - ACCOUNT_POST_PAGE_SIZE))}>Previous</button>
          <span>{currentPage}{totalPages ? ` / ${totalPages}` : ''}</span>
          <button className="pool-detail-btn" type="button" disabled={state?.loading || !canGoNext} onClick={() => onPage(offset + ACCOUNT_POST_PAGE_SIZE)}>Next</button>
        </div>
      </div>

      {state?.loading ? <div className="pool-empty">Loading posts...</div> : null}
      {state?.error ? <div className="pool-empty">{state.error}</div> : null}
      {!state?.loading && !state?.error && !rows.length ? <div className="pool-empty">No posts found for this account.</div> : null}

      {rows.length ? (
        <div className="pool-post-grid">
          {rows.map(item => <PoolPostCard item={item} key={String(item.post?.id || item.post?.reelfarm_post_id || item.material?.id || item.material?.reelfarm_video_id)} />)}
        </div>
      ) : null}
    </div>
  );
}

function PoolPostCard({ item }: { item: DetailedPostRow }) {
  const material = item.material || {};
  const post = item.post || {};
  const metrics = item.metrics || {};
  const images = (Array.isArray(material.slideshow_images) ? material.slideshow_images : []) as Array<{ image_url?: string } | string>;
  const [slideIndex, setSlideIndex] = useState(0);
  const currentIndex = Math.min(slideIndex, Math.max(0, images.length - 1));
  const currentImage = images[currentIndex];
  const currentImageUrl = typeof currentImage === 'string' ? currentImage : currentImage?.image_url;
  const title = material.hook || post.title || material.reelfarm_video_id || post.reelfarm_post_id || 'Untitled post';
  const publishedAt = post.published_at_readable || formatUtcReadable(post.published_at || '');

  function moveSlide(direction: number) {
    if (images.length <= 1) return;
    setSlideIndex(previous => (previous + direction + images.length) % images.length);
  }

  return (
    <article className="pool-post-card">
      <div className="pool-post-thumb">
        {currentImageUrl ? (
          <>
            <img src={currentImageUrl} alt="" loading="lazy" decoding="async" />
            {images.length > 1 ? (
              <>
                <button className="slide-nav prev" type="button" onClick={() => moveSlide(-1)} aria-label="Previous slide">‹</button>
                <button className="slide-nav next" type="button" onClick={() => moveSlide(1)} aria-label="Next slide">›</button>
                <span className="slide-counter">{currentIndex + 1}/{images.length}</span>
              </>
            ) : null}
          </>
        ) : <span>No image</span>}
      </div>
      <div className="pool-post-body">
        <h3>{title}</h3>
        <p>{publishedAt ? `Published ${publishedAt}` : material.status || post.status || 'No publish time'}</p>
        <div className="pool-post-metrics">
          <span><strong>{formatNumber(metrics.view_count || 0)}</strong> Views</span>
          <span><strong>{formatNumber(metrics.like_count || 0)}</strong> Likes</span>
          <span><strong>{formatNumber(metrics.comment_count || 0)}</strong> Comments</span>
          <span><strong>{formatNumber(metrics.share_count || 0)}</strong> Shares</span>
        </div>
      </div>
    </article>
  );
}
