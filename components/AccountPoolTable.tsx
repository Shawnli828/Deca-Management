import { Fragment } from 'react';
import { countryFlag, formatNumber, formatUtcReadable } from '@/lib/utils';
import {
  type AccountPoolDataSource,
  type AccountPoolRow,
  type ViewSortDirection,
  getAccountAvgViews,
  getAutomationDisplay,
  getPublishMethod
} from './AccountPoolHelpers';
import { AccountPostPanel, type AccountPostState } from './CountryAccountPosts';
import { accountTagStyle, nonIssueTags } from './CountryAccountTags';
import { formatTagLabel } from './ReelFarmAccountCard';

export function AccountPoolTable({
  rows,
  loading,
  viewSort,
  dataSource,
  expandedAccounts,
  postCache,
  accountRowKey,
  onToggleViewSort,
  onToggleAccount,
  onPagePosts,
  onRemoveTag,
  onEditTags
}: {
  rows: AccountPoolRow[];
  loading: boolean;
  viewSort: ViewSortDirection;
  dataSource: AccountPoolDataSource;
  expandedAccounts: Record<string, boolean>;
  postCache: Record<string, AccountPostState>;
  accountRowKey: (row: AccountPoolRow) => string;
  onToggleViewSort: () => void;
  onToggleAccount: (row: AccountPoolRow) => void;
  onPagePosts: (row: AccountPoolRow, offset: number) => void;
  onRemoveTag: (row: AccountPoolRow, tag: string) => void;
  onEditTags: (accountId: string) => void;
}) {
  return (
    <div className="account-pool-table-wrap">
      <table className="account-pool-table">
        <thead>
          <tr>
            <th><input type="checkbox" aria-label="Select all accounts" /></th>
            <th>Account</th>
            <th>
              <button className="pool-sort-head" type="button" onClick={onToggleViewSort} aria-label="Sort by average views">
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
          ) : rows.length ? rows.map(row => {
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
                        onClick={() => onToggleAccount(row)}
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
                          onClick={() => onRemoveTag(row, tag)}
                          title="点击删除这个 Tag"
                        >
                          {formatTagLabel(tag)} <span>×</span>
                        </button>
                      ))}
                      <button className="pool-tag-add" type="button" onClick={() => onEditTags(row.account_id)} title="添加 Tag">+</button>
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
                        onPage={offset => onPagePosts(row, offset)}
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
  );
}
