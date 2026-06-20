import { api } from '@/lib/api';
import type { AccountQueryResponse } from '@/lib/api/types';
import type { AccountPoolDataSource } from '@/lib/domain/accountPool';
import type { AccountSummary, Country } from '@/lib/types';
import {
  attachAccountTagsAndIssues,
  buildAccountPoolQueryParams,
  fetchAccountTagsAndIssues
} from '../accountPoolStateHelpers';

type LoadAccountPoolRowsOptions = {
  productCode: string;
  countries: Country[];
  dateFrom: string;
  dateTo: string;
  dataSource: AccountPoolDataSource;
};

export async function loadAccountPoolRows({
  productCode,
  countries,
  dateFrom,
  dateTo,
  dataSource
}: LoadAccountPoolRowsOptions) {
  const productTagsRequest = api.productTags(productCode).catch(() => ({
    ok: false,
    product_code: productCode,
    tags: [] as string[]
  }));
  const productTagsPayload = await productTagsRequest;

  if (!countries.length) {
    return {
      rows: [],
      productTags: productTagsPayload.tags || [],
      failures: []
    };
  }

  const countryPayloads = await Promise.allSettled(
    countries.map(async country => {
      const params = buildAccountPoolQueryParams({ productCode, country, dateFrom, dateTo, dataSource });
      const payload = await api.dataQuery<AccountQueryResponse>(params);
      return (payload.data || []).map(account => ({ ...account, country }));
    })
  );

  const accounts = countryPayloads
    .flatMap(result => result.status === 'fulfilled' ? result.value : [])
    .filter((account): account is AccountSummary & { country: Country } => Boolean(account));
  const failures = countryPayloads
    .map((result, index) => result.status === 'rejected'
      ? `${countries[index]?.name || 'Unknown'}: ${result.reason?.message || 'Request failed'}`
      : ''
    )
    .filter(Boolean);

  if (!accounts.length && failures.length) {
    throw new Error(failures.join('; '));
  }

  const accountIds = accounts.map(account => account.account_id).filter(Boolean);
  const { tagMap, issueMap } = await fetchAccountTagsAndIssues(accountIds);

  return {
    rows: attachAccountTagsAndIssues(accounts, tagMap, issueMap),
    productTags: productTagsPayload.tags || [],
    failures
  };
}
