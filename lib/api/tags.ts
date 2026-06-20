import { apiFetch, jsonPostInit } from './client';

export const tagsApi = {
  accountTags: (accountIds: string[]) =>
    apiFetch<{ ok: boolean; tags: Record<string, string[]> }>(`/api/account-tags?account_ids=${encodeURIComponent(accountIds.join(','))}`),
  addAccountTag: (accountId: string, tag: string) =>
    apiFetch<{ ok: boolean; account_id: string; tag: string }>('/api/account-tags', jsonPostInit({ account_id: accountId, tag })),
  deleteAccountTag: (accountId: string, tag: string) =>
    apiFetch<{ ok: boolean; account_id: string; tag: string }>('/api/account-tags/delete', jsonPostInit({ account_id: accountId, tag })),
  accountIssues: (accountIds: string[]) =>
    apiFetch<{ ok: boolean; issues: Record<string, string[]> }>(`/api/account-issues?account_ids=${encodeURIComponent(accountIds.join(','))}`),
  addAccountIssue: (accountId: string, issue: string) =>
    apiFetch<{ ok: boolean; account_id: string; issue: string }>('/api/account-issues', jsonPostInit({ account_id: accountId, issue })),
  deleteAccountIssue: (accountId: string, issue: string) =>
    apiFetch<{ ok: boolean; account_id: string; issue: string }>('/api/account-issues/delete', jsonPostInit({ account_id: accountId, issue })),
  productTags: (productCode: string) =>
    apiFetch<{ ok: boolean; product_code: string; tags: string[] }>(`/api/product-tags?product_code=${encodeURIComponent(productCode)}`),
  createProductTag: (productCode: string, tag: string) =>
    apiFetch<{ ok: boolean; product_code: string; tags: string[] }>('/api/product-tags', jsonPostInit({ product_code: productCode, tag })),
  deleteProductTag: (productCode: string, tag: string, removeAssignments = true) =>
    apiFetch<{ ok: boolean; product_code: string; tags: string[]; deleted_tag: string; removed_account_tags: number }>(
      '/api/product-tags/delete',
      jsonPostInit({ product_code: productCode, tag, remove_assignments: removeAssignments })
    )
};
