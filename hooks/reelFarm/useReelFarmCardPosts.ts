import { useCallback, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
import {
  buildAccountPostCacheKey,
  findReelFarmCard,
  getCardPostAccountId,
  mergeAccountPostRowsIntoResults,
  setReelFarmCardPostError,
  type ReelFarmPostPagination
} from '@/lib/reelFarmDashboardState';
import type { Country, DetailedPostRow, Product, ReelFarmResult } from '@/lib/types';
import { cardStateKey, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

type PostCacheEntry = {
  data: DetailedPostRow[];
  pagination: ReelFarmPostPagination;
};

type UseReelFarmCardPostsOptions = {
  selectedProduct: Product | null;
  selectedCountry: Country | null;
  days: number;
  reelFarmResults: Record<string, ReelFarmResult>;
  setReelFarmResults: React.Dispatch<React.SetStateAction<Record<string, ReelFarmResult>>>;
};

export function useReelFarmCardPosts({
  selectedProduct,
  selectedCountry,
  days,
  reelFarmResults,
  setReelFarmResults
}: UseReelFarmCardPostsOptions) {
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [postLoading, setPostLoading] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, PostCacheEntry>>({});
  const [slideIndexes, setSlideIndexes] = useState<Record<string, number>>({});

  const findCard = useCallback((cardKey: string) => {
    return findReelFarmCard(reelFarmResults, cardKey);
  }, [reelFarmResults]);

  const loadPosts = useCallback(async (cardKey: string, offset = 0) => {
    const product = selectedProduct;
    const country = selectedCountry;
    const card = findCard(cardKey);
    if (!product || !country || !card) return;
    const accountId = getCardPostAccountId(card);
    const cacheKey = buildAccountPostCacheKey(product, country, String(accountId), days, offset);
    const cached = postCache[cacheKey];

    function updateCard(data: DetailedPostRow[], pagination: ReelFarmPostPagination) {
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
      const data = payload.data || [];
      setPostCache(prev => ({ ...prev, [cacheKey]: { data, pagination } }));
      updateCard(data, pagination);
    } catch (error: unknown) {
      setReelFarmResults(prev => setReelFarmCardPostError({
        results: prev,
        product,
        country,
        cardKey,
        message: getErrorMessage(error, 'Posts loading failed.')
      }));
    } finally {
      setPostLoading(prev => {
        const next = { ...prev };
        delete next[cardKey];
        return next;
      });
    }
  }, [days, findCard, postCache, selectedCountry, selectedProduct, setReelFarmResults]);

  const toggleCard = useCallback((cardKey: string) => {
    setExpandedCards(prev => {
      const next = { ...prev, [cardKey]: !prev[cardKey] };
      if (next[cardKey]) void loadPosts(cardKey, 0);
      return next;
    });
  }, [loadPosts]);

  const pagePosts = useCallback((cardKey: string, direction: number) => {
    const card = findCard(cardKey);
    const limit = Number(card?.pagination?.limit) || 4;
    const offset = Number(card?.pagination?.offset) || 0;
    void loadPosts(cardKey, Math.max(0, offset + direction * limit));
  }, [findCard, loadPosts]);

  const moveSlide = useCallback((videoId: string, direction: number, total: number) => {
    setSlideIndexes(prev => ({ ...prev, [videoId]: ((prev[videoId] || 0) + direction + total) % total }));
  }, []);

  const resetCardPostState = useCallback(() => {
    setPostCache({});
    setPostLoading({});
    setExpandedCards({});
    setSlideIndexes({});
  }, []);

  return {
    expandedCards,
    postLoading,
    slideIndexes,
    loadPosts,
    toggleCard,
    pagePosts,
    moveSlide,
    resetCardPostState
  };
}
