import type { Product, PublishCheckAccount, PublishCheckAssignment } from './types';

export type PublishAssignmentSort = 'person' | 'product' | 'country';

export function publishAccountLabel(account: PublishCheckAccount) {
  return account.username || account.display_name || account.reelfarm_account_id || account.account_id || 'Unknown account';
}

export function formatPublishUtcTime(value?: string) {
  if (!value) return '暂无记录';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getUTCFullYear()}/${String(date.getUTCMonth() + 1).padStart(2, '0')}/${String(date.getUTCDate()).padStart(2, '0')} ${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')} UTC`;
}

export function publishCheckPeople(assignments: PublishCheckAssignment[]) {
  const seen = new Set<string>();
  return assignments
    .filter(item => {
      const key = item.person_id || item.person_name;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map(item => ({ id: item.person_id || item.person_name, name: item.person_name || item.person_id }));
}

export function sortPublishCheckAssignments(
  assignments: PublishCheckAssignment[],
  products: Product[],
  assignmentSort: PublishAssignmentSort
) {
  return [...assignments].sort((left, right) => {
    const leftProduct = products.find(product => product.id === left.product_id);
    const rightProduct = products.find(product => product.id === right.product_id);
    const leftCountry = leftProduct?.countries?.find(country => country.id === left.country_id);
    const rightCountry = rightProduct?.countries?.find(country => country.id === right.country_id);
    const values = {
      person: [left.person_name, right.person_name],
      product: [leftProduct?.name || '', rightProduct?.name || ''],
      country: [leftCountry?.name || '', rightCountry?.name || '']
    }[assignmentSort];
    const primary = String(values[0] || '').localeCompare(String(values[1] || ''), 'zh-Hans');
    if (primary !== 0) return primary;
    return String(left.person_name || '').localeCompare(String(right.person_name || ''), 'zh-Hans');
  });
}
