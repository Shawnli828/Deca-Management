'use client';

import { Fragment, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import {
  DATE_PRESETS,
  addDays,
  addMonths,
  dateInputValue,
  defaultDateRange,
  displayDateRange,
  parseInputDate,
  rangeForPreset,
  sameDate,
  type DatePresetKey
} from '@/lib/dateRange';
import type { AccountSummary, Country, DetailedPostRow, Product, ProductKpis } from '@/lib/types';
import { countryFlag, formatNumber, formatUtcReadable, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';
import { ACCOUNT_POST_PAGE_SIZE, AccountPostPanel, type AccountPostState } from './CountryAccountPosts';
import {
  AccountTagEditorModal,
  CategoryTagFilter,
  accountTagStyle,
  nonIssueTags,
  type AccountTagRow,
  type TagFilterRow
} from './CountryAccountTags';
import { formatTagLabel, getTagCategory } from './ReelFarmAccountCard';

type AccountPoolRow = AccountTagRow;
type ViewSortDirection = 'none' | 'desc' | 'asc';

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

function getPublishMethod(row: AccountPoolRow, dataSource: 'reelfarm' | 'museon_clone') {
  const storedMethod = String(row.publish_method || '').trim().toLowerCase();
  if (['manual', 'api', 'rpa'].includes(storedMethod)) return storedMethod;

  const postMode = String(row.post_mode || '').trim().toUpperCase();
  if (postMode === 'MEDIA_UPLOAD') return 'manual';
  if (postMode === 'DIRECT_POST') return 'api';
  if (postMode === 'RPA') return 'rpa';

  const sourceText = [
    row.data_source,
    row.automation_names,
    row.automation_name,
    row.campaign_name
  ].filter(Boolean).join(' ').toLowerCase();
  if (sourceText.includes('manual')) return 'manual';
  if (sourceText.includes('api') || sourceText.includes('museon')) return 'api';
  if (sourceText.includes('rpa') || sourceText.includes('reelfarm')) return 'rpa';
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
  const [publishMethodFilter, setPublishMethodFilter] = useState('all');
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
      const issueMap: Record<string, string[]> = {};
      for (let index = 0; index < accountIds.length; index += 80) {
        const batch = accountIds.slice(index, index + 80);
        const [tagPayload, issuePayload] = await Promise.all([
          api.accountTags(batch),
          api.accountIssues(batch)
        ]);
        Object.assign(tagMap, tagPayload.tags || {});
        Object.assign(issueMap, issuePayload.issues || {});
      }
      setRows(accounts.map(account => ({
        ...account,
        tags: tagMap[account.account_id] || [],
        issues: issueMap[account.account_id] || []
      })));
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

  async function deleteProductTagOption(tag: string) {
    const productCode = getProductReelFarmCode(product);
    const nextTag = tag.trim();
    if (!productCode || !nextTag) return;
    const confirmed = window.confirm(`删除 ${formatTagLabel(nextTag)} 吗？这个 Tag 会从当前产品所有账号上移除。`);
    if (!confirmed) return;
    const payload = await api.deleteProductTag(productCode, nextTag, true);
    const deletedTag = (payload.deleted_tag || nextTag).toLowerCase();
    setProductTagOptions(payload.tags || []);
    setRows(previous => previous.map(item => ({
      ...item,
      tags: (item.tags || []).filter(value => value.toLowerCase() !== deletedTag)
    })));
    setTagFilters(previous => previous
      .map(filter => ({
        ...filter,
        tags: filter.tags.filter(value => value.toLowerCase() !== deletedTag)
      }))
      .filter(filter => filter.tags.length)
    );
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
    const publishMethod = getPublishMethod(row, dataSource);
    if (query && !username.includes(query)) return false;
    if (countryFilter !== 'all' && countryCode !== countryFilter) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    if (publishMethodFilter !== 'all' && publishMethod !== publishMethodFilter) return false;
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
    const hasAccountCoverageFields = filteredRows.some(
      row => row.posted_account_count !== undefined || row.expected_account_count !== undefined
    );
    const postedAccounts = hasAccountCoverageFields
      ? filteredRows.reduce((sum, row) => sum + (Number(row.posted_account_count) || 0), 0)
      : filteredRows.filter(row => (Number(row.post_count) || 0) > 0).length;
    const expectedAccounts = hasAccountCoverageFields
      ? filteredRows.reduce((sum, row) => sum + (Number(row.expected_account_count) || 0), 0)
      : filteredRows.length;
    const posts = filteredRows.reduce((sum, row) => sum + (Number(row.post_count) || 0), 0);
    const views = filteredRows.reduce((sum, row) => sum + (Number(row.total_views) || 0), 0);
    const likes = filteredRows.reduce((sum, row) => sum + (Number(row.total_likes) || 0), 0);
    const comments = filteredRows.reduce((sum, row) => sum + (Number(row.total_comments) || 0), 0);
    const shares = filteredRows.reduce((sum, row) => sum + (Number(row.total_shares) || 0), 0);
    const avgViews = posts ? Math.round(views / posts) : 0;
    const engagement = views ? ((likes + comments + shares) / views) * 100 : 0;

    return [
      { label: 'POSTED', value: `${formatNumber(postedAccounts)}/${formatNumber(expectedAccounts)}`, note: 'Posted accounts / expected active accounts' },
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
        <select className="text-input" value={publishMethodFilter} onChange={event => setPublishMethodFilter(event.target.value)}>
          <option value="all">All Publish Methods</option>
          <option value="manual">manual</option>
          <option value="api">api</option>
          <option value="rpa">rpa</option>
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
              <th>Publish Method</th>
              <th>Country</th>
              <th>Status</th>
              <th>Posts</th>
              <th>Tags</th>
              <th>Issues</th>
              <th>Synced</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={11} className="pool-empty">Loading accounts...</td></tr>
            ) : sortedRows.length ? sortedRows.map(row => {
              const avgViews = getAccountAvgViews(row);
              const rowKey = accountRowKey(row);
              const isExpanded = Boolean(expandedAccounts[rowKey]);
              const automationDisplay = getAutomationDisplay(row, dataSource);
              const publishMethod = getPublishMethod(row, dataSource);
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
                    <td><span className={`pool-method-pill ${publishMethod}`}>{publishMethod}</span></td>
                    <td>{countryFlag(row.country)} {row.country.name}</td>
                    <td><span className="pool-pill">{row.status || 'N/A'}</span></td>
                    <td>{formatNumber(row.post_count || 0)}</td>
                    <td>
                      <div className="pool-tags">
                        {nonIssueTags(row.tags).map(tag => (
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
                    <td>
                      <div className="pool-issues">
                        {(row.issues || []).length ? (row.issues || []).map(issue => (
                          <span className="pool-issue-badge" key={issue}>{issue}</span>
                        )) : <span className="pool-issue-empty">—</span>}
                      </div>
                    </td>
                    <td>{row.last_synced_at ? formatUtcReadable(row.last_synced_at) : '—'}</td>
                  </tr>
                  {isExpanded ? (
                    <tr className="account-posts-row" key={`${rowKey}:posts`}>
                      <td colSpan={11}>
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
              <tr><td colSpan={11} className="pool-empty">No accounts match the current filters.</td></tr>
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
          onDeleteProductTag={deleteProductTagOption}
        />
      ) : null}
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
