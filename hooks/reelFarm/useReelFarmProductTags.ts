import { useCallback, useState } from 'react';
import { api } from '@/lib/api';
import type { Product } from '@/lib/types';
import { getProductReelFarmCode } from '@/lib/utils';

export function useReelFarmProductTags() {
  const [productTags, setProductTags] = useState<Record<string, string[]>>({});

  const setProductTagOptions = useCallback((productCode: string, tags: string[]) => {
    setProductTags(previous => ({ ...previous, [productCode]: tags }));
  }, []);

  const loadProductTags = useCallback(async (product?: Product | null) => {
    if (!product) return [];
    const productCode = getProductReelFarmCode(product);
    const payload = await api.productTags(productCode);
    const tags = payload.tags || [];
    setProductTagOptions(productCode, tags);
    return tags;
  }, [setProductTagOptions]);

  return {
    productTags,
    loadProductTags,
    setProductTagOptions
  };
}
