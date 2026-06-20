import { apiFetch, withQuery } from './client';
import type {
  AccountQueryResponse,
  DetailedRowsResponse,
  ProductKpisResponse,
  ProductRollupsResponse
} from './types';

export const dataQueryApi = {
  dataQuery: <T>(params: URLSearchParams) => apiFetch<T>(withQuery('/api/data/query', params)),
  productKpis: (productCode: string, countryCode?: string, source?: string) =>
    dataQueryApi.dataQuery<ProductKpisResponse>(
      new URLSearchParams({
        resource: 'product_kpis',
        product_code: productCode,
        ...(countryCode ? { country_code: countryCode } : {}),
        ...(source ? { source } : {})
      })
    ),
  productRollups: (source?: string) =>
    dataQueryApi.dataQuery<ProductRollupsResponse>(
      new URLSearchParams({ resource: 'product_rollups', ...(source ? { source } : {}) })
    ),
  accounts: (productCode: string, countryCode: string, days: number, source?: string) =>
    dataQueryApi.dataQuery<AccountQueryResponse>(
      new URLSearchParams({
        resource: 'accounts',
        product_code: productCode,
        country_code: countryCode,
        days: String(days),
        ...(source ? { source } : {})
      })
    ),
  accountPosts: (productCode: string, countryCode: string, accountId: string, days: number, limit: number, offset: number, source?: string) =>
    dataQueryApi.dataQuery<DetailedRowsResponse>(
      new URLSearchParams({
        resource: 'account_posts',
        product_code: productCode,
        country_code: countryCode,
        account_id: accountId,
        days: String(days),
        limit: String(limit),
        offset: String(offset),
        ...(source ? { source } : {})
      })
    )
};
