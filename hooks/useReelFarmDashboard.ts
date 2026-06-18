'use client';

import { useEffect, useState } from 'react';
import { accountSummaryToCard, api, mergePostRowsIntoCard } from '@/lib/api';
import type { Country, Product, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import {
  buildCountryAutomationPrefix,
  cardStateKey,
  getCountryReelFarmCode,
  getProductReelFarmCode
} from '@/lib/utils';

type PageState = 'products' | 'product' | 'country';

type PostCacheEntry = {
  data: any[];
  pagination: {
    limit: number;
    offset: number;
    has_more: boolean;
    total?: number;
  };
};

type UseReelFarmDashboardOptions = {
  authenticated: boolean;
  page: PageState;
  selectedProduct: Product | null;
  selectedCountry: Country | null;
  selectedProductId: string;
  selectedCountryId: string;
};

export function useReelFarmDashboard({
  authenticated,
  page,
  selectedProduct,
  selectedCountry,
  selectedProductId,
  selectedCountryId
}: UseReelFarmDashboardOptions) {
  const [days, setDays] = useState(30);
  const [reelFarmResults, setReelFarmResults] = useState<Record<string, ReelFarmResult>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [postLoading, setPostLoading] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, PostCacheEntry>>({});
  const [slideIndexes, setSlideIndexes] = useState<Record<string, number>>({});
  const [productTags, setProductTags] = useState<Record<string, string[]>>({});

  function resetReelFarmState(options: { includeResults?: boolean } = {}) {
    const includeResults = options.includeResults !== false;
    if (includeResults) setReelFarmResults({});
    setPostCache({});
    setPostLoading({});
    setExpandedCards({});
    setSlideIndexes({});
  }

  function getCardAccountId(card: ReelFarmCard) {
    const account = card.account || {};
    return String(account.id || account.account_id || '').trim();
  }

  async function loadProductTags(product = selectedProduct) {
    if (!product) return [];
    const productCode = getProductReelFarmCode(product);
    const payload = await api.productTags(productCode);
    setProductTags(previous => ({ ...previous, [productCode]: payload.tags || [] }));
    return payload.tags || [];
  }

  async function loadAccounts(product = selectedProduct, country = selectedCountry, force = false, daysOverride = days) {
    if (!product || !country) return;
    const prefix = buildCountryAutomationPrefix(product, country);
    if (!force && reelFarmResults[prefix]) return;

    setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], loading: true } }));
    try {
      await loadProductTags(product);
      const payload = await api.accounts(getProductReelFarmCode(product), getCountryReelFarmCode(country), daysOverride);
      let cards = (payload.data || []).map(accountSummaryToCard);
      const accountIds = cards.map(getCardAccountId).filter(Boolean);
      if (accountIds.length) {
        const tagPayload = await api.accountTags(accountIds);
        cards = cards.map(card => ({ ...card, tags: tagPayload.tags[getCardAccountId(card)] || [] }));
      }
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: cards.length, cards } }));
    } catch (error: any) {
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], error: error?.message || '账号数据加载失败' } }));
    }
  }

  function updateCardTags(accountId: string, updater: (tags: string[]) => string[]) {
    setReelFarmResults(prev => {
      const next = { ...prev };
      for (const [prefix, result] of Object.entries(next)) {
        next[prefix] = {
          ...result,
          cards: result.cards.map(card => getCardAccountId(card) === accountId ? { ...card, tags: updater(card.tags || []) } : card)
        };
      }
      return next;
    });
  }

  async function addCardTag(card: ReelFarmCard, tag: string) {
    const accountId = getCardAccountId(card);
    if (!accountId) return;
    if (!tag?.trim()) return;
    const product = selectedProduct;
    if (product) {
      const productCode = getProductReelFarmCode(product);
      const productTagPayload = await api.createProductTag(productCode, tag.trim());
      setProductTags(previous => ({ ...previous, [productCode]: productTagPayload.tags || [] }));
    }
    const payload = await api.addAccountTag(accountId, tag.trim());
    updateCardTags(accountId, previous => Array.from(new Set([...previous, payload.tag])));
  }

  async function removeCardTag(card: ReelFarmCard, tag: string) {
    const accountId = getCardAccountId(card);
    if (!accountId) return;
    await api.deleteAccountTag(accountId, tag);
    updateCardTags(accountId, previous => previous.filter(item => item !== tag));
  }

  function findCard(cardKey: string) {
    for (const result of Object.values(reelFarmResults)) {
      const card = result.cards.find(item => cardStateKey(item) === cardKey);
      if (card) return card;
    }
    return null;
  }

  async function loadPosts(cardKey: string, offset = 0) {
    const product = selectedProduct;
    const country = selectedCountry;
    const card = findCard(cardKey);
    if (!product || !country || !card) return;
    const account = card.account || {};
    const accountId = account.id || account.account_id || account.reelfarm_account_id || account.tiktok_account_id || account.username || account.account_username || '';
    const cacheKey = [getProductReelFarmCode(product), getCountryReelFarmCode(country), accountId, days, offset].join('|');
    const cached = postCache[cacheKey];

    function updateCard(data: any[], pagination: PostCacheEntry['pagination']) {
      const prefix = buildCountryAutomationPrefix(product, country);
      setReelFarmResults(prev => {
        const result = prev[prefix];
        if (!result) return prev;
        const cards = result.cards.map(item => {
          if (cardStateKey(item) !== cardKey) return item;
          const clone = structuredClone(item);
          mergePostRowsIntoCard(clone, data);
          clone.pagination = pagination;
          return clone;
        });
        return { ...prev, [prefix]: { ...result, cards } };
      });
    }

    if (cached) {
      updateCard(cached.data, cached.pagination);
      return;
    }

    setPostLoading(prev => ({ ...prev, [cardKey]: true }));
    try {
      const payload = await api.accountPosts(getProductReelFarmCode(product), getCountryReelFarmCode(country), String(accountId), days, 4, offset);
      const pagination = payload.pagination || { limit: 4, offset, has_more: false, total: payload.data?.length || 0 };
      setPostCache(prev => ({ ...prev, [cacheKey]: { data: payload.data || [], pagination } }));
      updateCard(payload.data || [], pagination);
    } catch (error: any) {
      setReelFarmResults(prev => {
        const prefix = buildCountryAutomationPrefix(product, country);
        const result = prev[prefix];
        if (!result) return prev;
        const cards = result.cards.map(item => cardStateKey(item) === cardKey ? { ...item, errors: { videos: null, posts: error?.message || 'Posts loading failed.' } } : item);
        return { ...prev, [prefix]: { ...result, cards } };
      });
    } finally {
      setPostLoading(prev => {
        const next = { ...prev };
        delete next[cardKey];
        return next;
      });
    }
  }

  function toggleCard(cardKey: string) {
    setExpandedCards(prev => {
      const next = { ...prev, [cardKey]: !prev[cardKey] };
      if (next[cardKey]) loadPosts(cardKey, 0);
      return next;
    });
  }

  function pagePosts(cardKey: string, direction: number) {
    const card = findCard(cardKey);
    const limit = Number(card?.pagination?.limit) || 4;
    const offset = Number(card?.pagination?.offset) || 0;
    loadPosts(cardKey, Math.max(0, offset + direction * limit));
  }

  function moveSlide(videoId: string, direction: number, total: number) {
    setSlideIndexes(prev => ({ ...prev, [videoId]: ((prev[videoId] || 0) + direction + total) % total }));
  }

  function changeDays(nextDays: number) {
    if (![7, 14, 30].includes(nextDays)) return;
    setDays(nextDays);
    resetReelFarmState();
    setTimeout(() => loadAccounts(selectedProduct, selectedCountry, true, nextDays), 0);
  }

  useEffect(() => {
    if (authenticated && selectedProduct) {
      loadProductTags(selectedProduct).catch(() => {});
    }
  }, [authenticated, selectedProductId]);

  useEffect(() => {
    if (authenticated && page === 'country') {
      loadAccounts(selectedProduct, selectedCountry, false);
    }
  }, [authenticated, page, selectedProductId, selectedCountryId]);

  return {
    days,
    reelFarmResults,
    expandedCards,
    postLoading,
    slideIndexes,
    productTags,
    loadAccounts,
    addCardTag,
    removeCardTag,
    changeDays,
    toggleCard,
    pagePosts,
    moveSlide,
    resetReelFarmState
  };
}
