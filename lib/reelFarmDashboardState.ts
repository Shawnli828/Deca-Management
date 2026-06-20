import { mergePostRowsIntoCard } from '@/lib/reelfarmCardAdapters';
import type { Country, DetailedPostRow, Product, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import {
  buildCountryAutomationPrefix,
  cardStateKey,
  getCountryReelFarmCode,
  getProductReelFarmCode
} from '@/lib/utils';

export type ReelFarmPostPagination = {
  limit: number;
  offset: number;
  has_more: boolean;
  total?: number;
};

export function getCardAccountId(card: ReelFarmCard) {
  const account = card.account || {};
  return String(account.id || account.account_id || '').trim();
}

export function getCardPostAccountId(card: ReelFarmCard) {
  const account = card.account || {};
  return account.id
    || account.account_id
    || account.reelfarm_account_id
    || account.tiktok_account_id
    || account.username
    || account.account_username
    || '';
}

export function buildAccountPostCacheKey(product: Product, country: Country, accountId: string, days: number, offset: number) {
  return [getProductReelFarmCode(product), getCountryReelFarmCode(country), accountId, days, offset].join('|');
}

export function findReelFarmCard(results: Record<string, ReelFarmResult>, cardKey: string) {
  for (const result of Object.values(results)) {
    const card = result.cards.find(item => cardStateKey(item) === cardKey);
    if (card) return card;
  }
  return null;
}

export function updateReelFarmCardTags(
  results: Record<string, ReelFarmResult>,
  accountId: string,
  updater: (tags: string[]) => string[]
) {
  const next = { ...results };
  for (const [prefix, result] of Object.entries(next)) {
    next[prefix] = {
      ...result,
      cards: result.cards.map(card => getCardAccountId(card) === accountId ? { ...card, tags: updater(card.tags || []) } : card)
    };
  }
  return next;
}

export function mergeAccountPostRowsIntoResults({
  results,
  product,
  country,
  cardKey,
  data,
  pagination
}: {
  results: Record<string, ReelFarmResult>;
  product: Product;
  country: Country;
  cardKey: string;
  data: DetailedPostRow[];
  pagination: ReelFarmPostPagination;
}) {
  const prefix = buildCountryAutomationPrefix(product, country);
  const result = results[prefix];
  if (!result) return results;
  const cards = result.cards.map(item => {
    if (cardStateKey(item) !== cardKey) return item;
    const clone = structuredClone(item);
    mergePostRowsIntoCard(clone, data);
    clone.pagination = pagination;
    return clone;
  });
  return { ...results, [prefix]: { ...result, cards } };
}

export function setReelFarmCardPostError({
  results,
  product,
  country,
  cardKey,
  message
}: {
  results: Record<string, ReelFarmResult>;
  product: Product;
  country: Country;
  cardKey: string;
  message: string;
}) {
  const prefix = buildCountryAutomationPrefix(product, country);
  const result = results[prefix];
  if (!result) return results;
  const cards = result.cards.map(item => cardStateKey(item) === cardKey ? { ...item, errors: { videos: null, posts: message } } : item);
  return { ...results, [prefix]: { ...result, cards } };
}
