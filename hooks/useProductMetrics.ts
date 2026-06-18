import { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { Country, Product, ProductKpis, ProductRollup } from '@/lib/types';
import { getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

type UseProductMetricsOptions = {
  products: Product[];
  selectedProductId: string;
  onStatus: (message: string, isError?: boolean) => void;
};

function emptyCloneProducts(products: Product[]) {
  return products.map(product => ({
    ...product,
    creatorCount: 0,
    automationCount: 0,
    materialCount: 0,
    postCount: 0,
    countries: (product.countries || []).map(country => ({
      ...country,
      creatorCount: 0,
      automationCount: 0,
      materialCount: 0,
      postCount: 0,
      reelFarmSyncedAt: ''
    }))
  }));
}

function buildProductsFromRollups(sourceProducts: Product[], rollups: ProductRollup[]) {
  const rollupMap = new Map(
    (rollups || []).map(rollup => [String(rollup.product_code || '').toUpperCase(), rollup])
  );

  return sourceProducts.map(product => {
    const productCode = getProductReelFarmCode(product);
    const rollup = rollupMap.get(productCode);
    const countryRollups = new Map(
      (rollup?.countries || []).map(country => [String(country.country_code || '').toUpperCase(), country])
    );
    const countries = (product.countries || []).map(country => {
      const countryRollup = countryRollups.get(getCountryReelFarmCode(country));
      return {
        ...country,
        creatorCount: Number(countryRollup?.creator_count) || 0,
        materialCount: Number(countryRollup?.material_count) || 0,
        postCount: Number(countryRollup?.post_count) || 0,
        reelFarmSyncedAt: countryRollup?.last_synced_at || ''
      };
    });

    return {
      ...product,
      creatorCount: Number(rollup?.creator_count) || 0,
      materialCount: Number(rollup?.material_count) || 0,
      postCount: Number(rollup?.post_count) || 0,
      countries
    };
  });
}

export function useProductMetrics({ products, selectedProductId, onStatus }: UseProductMetricsOptions) {
  const [productKpis, setProductKpis] = useState<Record<string, ProductKpis | null>>({});
  const [cloneProducts, setCloneProducts] = useState<Product[]>([]);
  const [cloneProductKpis, setCloneProductKpis] = useState<Record<string, ProductKpis | null>>({});
  const [countryKpis, setCountryKpis] = useState<Record<string, ProductKpis | null>>({});

  const cloneDisplayProducts = useMemo(
    () => (cloneProducts.length ? cloneProducts : emptyCloneProducts(products)),
    [cloneProducts, products]
  );
  const selectedCloneProduct = useMemo(
    () => cloneDisplayProducts.find(product => product.id === selectedProductId) || cloneDisplayProducts[0] || null,
    [cloneDisplayProducts, selectedProductId]
  );

  async function loadProductKpis(product?: Product | null) {
    if (!product) return;
    try {
      const payload = await api.productKpis(getProductReelFarmCode(product));
      setProductKpis(prev => ({ ...prev, [product.id]: payload.data || null }));
    } catch {
      setProductKpis(prev => ({ ...prev, [product.id]: null }));
    }
  }

  async function loadCloneProductData(sourceProducts = products) {
    if (!sourceProducts.length) return;
    try {
      const rollupPayload = await api.productRollups('museon_clone');
      setCloneProducts(buildProductsFromRollups(sourceProducts, rollupPayload.data || []));
      const entries = await Promise.all(sourceProducts.map(async product => {
        try {
          const payload = await api.productKpis(getProductReelFarmCode(product), undefined, 'museon_clone');
          return [product.id, payload.data || null] as const;
        } catch {
          return [product.id, null] as const;
        }
      }));
      setCloneProductKpis(Object.fromEntries(entries));
    } catch (error: any) {
      setCloneProducts(buildProductsFromRollups(sourceProducts, []));
      setCloneProductKpis({});
      onStatus(error?.message || 'Clone Slide Show 数据加载失败', true);
    }
  }

  async function loadCountryKpis(product?: Product | null, country?: Country | null) {
    if (!product || !country) return;
    const key = `${product.id}:${country.id}`;
    try {
      const payload = await api.productKpis(getProductReelFarmCode(product), getCountryReelFarmCode(country));
      setCountryKpis(prev => ({ ...prev, [key]: payload.data || null }));
    } catch {
      setCountryKpis(prev => ({ ...prev, [key]: null }));
    }
  }

  return {
    productKpis,
    cloneDisplayProducts,
    selectedCloneProduct,
    cloneProductKpis,
    countryKpis,
    loadProductKpis,
    loadCloneProductData,
    loadCountryKpis
  };
}
