import type { Country, Product, ReelFarmCard } from './types';

export const countryCodes: Record<string, string> = {
  'United States': 'US',
  'United Kingdom': 'UK',
  Japan: 'JP',
  Germany: 'GE',
  Brazil: 'BR',
  India: 'IN',
  China: 'CN',
  France: 'FR',
  Italy: 'IT',
  Canada: 'CA',
  Australia: 'AU',
  'South Korea': 'KR'
};

export function formatNumber(value: unknown) {
  const number = Number(value) || 0;
  if (Math.abs(number) >= 1_000_000) return `${(number / 1_000_000).toFixed(1)}M`;
  if (Math.abs(number) >= 1_000) return `${(number / 1_000).toFixed(1)}K`;
  return new Intl.NumberFormat('en-US').format(number);
}

export function formatPercent(value: number) {
  return `${(Number(value) || 0).toFixed(1)}%`;
}

export function formatUtcReadable(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, '0');
  const d = String(date.getUTCDate()).padStart(2, '0');
  const h = String(date.getUTCHours()).padStart(2, '0');
  const min = String(date.getUTCMinutes()).padStart(2, '0');
  return `${y}/${m}/${d} ${h}:${min} UTC`;
}

export function codeFromName(value?: string) {
  const cleaned = String(value || '').replace(/[^a-zA-Z0-9 ]+/g, ' ').trim();
  if (!cleaned) return 'APP';
  const compact = cleaned.replace(/\s+/g, '');
  if (compact.toLowerCase() === 'delust') return 'DL';
  if (compact.length <= 4) return compact.toUpperCase();
  return cleaned.split(/\s+/).map(part => part[0]).join('').toUpperCase() || compact.slice(0, 4).toUpperCase();
}

export function getProductReelFarmCode(product?: Product | null) {
  return (product?.reelFarmCode || codeFromName(product?.name)).toUpperCase();
}

export function getCountryReelFarmCode(country?: Country | null) {
  return (country?.reelFarmCode || countryCodes[country?.name || ''] || codeFromName(country?.name)).toUpperCase();
}

export function countryFlag(country?: Country | null) {
  const code = getCountryReelFarmCode(country);
  const flags: Record<string, string> = {
    US: '🇺🇸',
    UK: '🇬🇧',
    GB: '🇬🇧',
    GE: '🇩🇪',
    DE: '🇩🇪',
    FR: '🇫🇷',
    IT: '🇮🇹',
    CA: '🇨🇦',
    BR: '🇧🇷',
    IN: '🇮🇳',
    CN: '🇨🇳',
    JP: '🇯🇵',
    KR: '🇰🇷',
    AU: '🇦🇺',
    AT: '🇦🇹'
  };
  return flags[code] || '🌐';
}

export function buildCountryAutomationPrefix(product?: Product | null, country?: Country | null) {
  return `${getCountryReelFarmCode(country)}-${getProductReelFarmCode(product)}`;
}

export function cardStateKey(card: ReelFarmCard) {
  const automation = card.automation || {};
  const account = card.account || {};
  return String(
    card.card_key ||
      automation.automation_id ||
      automation.title ||
      account.account_id ||
      account.id ||
      account.tiktok_account_id ||
      account.reelfarm_account_id ||
      account.account_username ||
      account.username ||
      ''
  );
}

export function getMetricFromPosts<T extends object>(posts: readonly T[], key: string) {
  return posts.reduce((sum, post) => sum + (Number((post as Record<string, unknown>)[key]) || 0), 0);
}

export function normalizeProductFolder(product: Product) {
  return product.folder || product.owner_type || '甲方';
}

export function createPersonId(name: string) {
  return name.trim().toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, '-').replace(/^-|-$/g, '') || crypto.randomUUID();
}
