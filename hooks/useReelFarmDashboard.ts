'use client';

import { useEffect, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import { useReelFarmCardPosts } from '@/hooks/reelFarm/useReelFarmCardPosts';
import { useReelFarmProductTags } from '@/hooks/reelFarm/useReelFarmProductTags';
import { accountSummaryToCard } from '@/lib/reelfarmCardAdapters';
import {
  getCardAccountId,
  updateReelFarmCardTags,
} from '@/lib/reelFarmDashboardState';
import type { Country, Product, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import {
  buildCountryAutomationPrefix,
  getCountryReelFarmCode,
  getProductReelFarmCode
} from '@/lib/utils';

type PageState = 'products' | 'product' | 'country';

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
  const { productTags, loadProductTags, setProductTagOptions } = useReelFarmProductTags();
  const {
    expandedCards,
    postLoading,
    slideIndexes,
    toggleCard,
    pagePosts,
    moveSlide,
    resetCardPostState
  } = useReelFarmCardPosts({
    selectedProduct,
    selectedCountry,
    days,
    reelFarmResults,
    setReelFarmResults
  });

  function resetReelFarmState(options: { includeResults?: boolean } = {}) {
    const includeResults = options.includeResults !== false;
    if (includeResults) setReelFarmResults({});
    resetCardPostState();
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
    } catch (error: unknown) {
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], error: getErrorMessage(error, '账号数据加载失败') } }));
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
      setProductTagOptions(productCode, productTagPayload.tags || []);
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
