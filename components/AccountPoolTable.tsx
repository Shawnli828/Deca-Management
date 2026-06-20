import {
  type AccountPoolDataSource,
  type AccountPoolRow,
  type ViewSortDirection
} from '@/lib/domain/accountPool';
import type { AccountPostState } from './CountryAccountPosts';
import { AccountPoolTableRow } from './AccountPoolTableRow';

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
            const rowKey = accountRowKey(row);
            const isExpanded = Boolean(expandedAccounts[rowKey]);
            return (
              <AccountPoolTableRow
                key={rowKey}
                row={row}
                rowKey={rowKey}
                isExpanded={isExpanded}
                dataSource={dataSource}
                postState={postCache[rowKey]}
                onToggleAccount={onToggleAccount}
                onPagePosts={onPagePosts}
                onRemoveTag={onRemoveTag}
                onEditTags={onEditTags}
              />
            );
          }) : (
            <tr><td colSpan={11} className="pool-empty">No accounts match the current filters.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
