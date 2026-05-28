'use client';

import { Fragment, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { AccountSummary, Country, DetailedPostRow, Product, ProductKpis } from '@/lib/types';
import { countryFlag, formatNumber, formatUtcReadable, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

type AccountPoolRow = AccountSummary & { country: Country; tags?: string[] };
type AccountPostState = {
  rows: DetailedPostRow[];
  loading: boolean;
  error: string;
  offset: number;
  hasMore: boolean;
  total?: number;
};

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
  const [rows, setRows] = useState<AccountPoolRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [countryFilter, setCountryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tagFilter, setTagFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState(defaultDateRange.from);
  const [dateTo, setDateTo] = useState(defaultDateRange.to);
  const [expandedAccounts, setExpandedAccounts] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, AccountPostState>>({});

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
      const chunks = await Promise.all(countries.map(async country => {
        const params = addDateFilters(new URLSearchParams({
          resource: 'accounts',
          product_code: productCode,
          country_code: getCountryReelFarmCode(country)
        }));
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
  }, [product.id, dateFrom, dateTo]);

  useEffect(() => {
    setExpandedAccounts({});
    setPostCache({});
  }, [product.id, dateFrom, dateTo]);

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
              const rowKey = accountRowKey(row);
              const isExpanded = Boolean(expandedAccounts[rowKey]);
              return (
                <Fragment key={rowKey}>
                  <tr key={rowKey}>
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
                    <td><button className="pool-detail-btn" type="button" onClick={() => toggleAccount(row)}>{isExpanded ? 'Close' : 'Details'}</button></td>
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
    </section>
  );
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
          <button className="pool-detail-btn" type="button" disabled={state?.loading || !state?.hasMore} onClick={() => onPage(offset + ACCOUNT_POST_PAGE_SIZE)}>Next</button>
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
  const images = Array.isArray(material.slideshow_images) ? material.slideshow_images : [];
  const firstImage = images.find(image => image?.image_url)?.image_url;
  const title = material.hook || post.title || material.reelfarm_video_id || post.reelfarm_post_id || 'Untitled post';
  const publishedAt = post.published_at_readable || formatUtcReadable(post.published_at || '');

  return (
    <article className="pool-post-card">
      <div className="pool-post-thumb">
        {firstImage ? <img src={firstImage} alt="" loading="lazy" decoding="async" /> : <span>No image</span>}
        {images.length ? <b>{images.length}</b> : null}
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
