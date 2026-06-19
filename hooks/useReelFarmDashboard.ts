'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { accountSummaryToCard } from '@/lib/reelfarmCardAdapters';
import {
  buildAccountPostCacheKey,
  findReelFarmCard,
  getCardAccountId,
  getCardPostAccountId,
  mergeAccountPostRowsIntoResults,
  setReelFarmCardPostError,
  updateReelFarmCardTags,
  type ReelFarmPostPagination
} from '@/lib/reelFarmDashboardState';
import type { Country, Product, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import {
  buildCountryAutomationPrefix,
  getCountryReelFarmCode,
  getProductReelFarmCode
} from '@/lib/utils';

type PageState = 'products' | 'product' | 'country';

type PostCacheEntry = {
  data: any[];
  pagination: ReelFarmPostPagination;
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
    setReelFarmResults(prev => updateReelFarmCardTags(prev, accountId, updater));
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
    return findReelFarmCard(reelFarmResults, cardKey);
  }

  async function loadPosts(cardKey: string, offset = 0) {
    const product = selectedProduct;
    const country = selectedCountry;
    const card = findCard(cardKey);
    if (!product || !country || !card) return;
    const accountId = getCardPostAccountId(card);
    const cacheKey = buildAccountPostCacheKey(product, country, String(accountId), days, offset);
    const cached = postCache[cacheKey];

    function updateCard(data: any[], pagination: ReelFarmPostPagination) {
      setReelFarmResults(prev => mergeAccountPostRowsIntoResults({ results: prev, product, country, cardKey, data, pagination }));
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
      setReelFarmResults(prev => setReelFarmCardPostError({
        results: prev,
        product,
        country,
        cardKey,
        message: error?.message || 'Posts loading failed.'
      }));
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
