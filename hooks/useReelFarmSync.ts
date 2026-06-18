'use client';

import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { api } from '@/lib/api';
import type { Country, Product } from '@/lib/types';
import {
  buildCountryAutomationPrefix,
  getCountryReelFarmCode,
  getProductReelFarmCode
} from '@/lib/utils';

type PageState = 'products' | 'product' | 'country';

type SyncResult = {
  creator_count?: number;
  material_count?: number;
  synced_at?: string;
};

type ResetReelFarmState = (options?: { includeResults?: boolean }) => void;

type UseReelFarmSyncOptions = {
  products: Product[];
  selectedProduct: Product | null;
  selectedCountry: Country | null;
  selectedProductId: string;
  page: PageState;
  setProducts: Dispatch<SetStateAction<Product[]>>;
  onStatus: (message: string, isError?: boolean) => void;
  resetReelFarmState: ResetReelFarmState;
  loadAccounts: (product?: Product | null, country?: Country | null, force?: boolean, daysOverride?: number) => Promise<void>;
  loadProductKpis: (product?: Product | null) => Promise<void>;
  loadCountryKpis: (product?: Product | null, country?: Country | null) => Promise<void>;
  loadCloneProductData: (sourceProducts?: Product[]) => Promise<void>;
};

function wait(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function useReelFarmSync({
  products,
  selectedProduct,
  selectedCountry,
  selectedProductId,
  page,
  setProducts,
  onStatus,
  resetReelFarmState,
  loadAccounts,
  loadProductKpis,
  loadCountryKpis,
  loadCloneProductData
}: UseReelFarmSyncOptions) {
  const [syncPrefix, setSyncPrefix] = useState('');
  const [syncProductId, setSyncProductId] = useState('');
  const [syncAllRunning, setSyncAllRunning] = useState(false);
  const [syncAllProgress, setSyncAllProgress] = useState('');

  function applySyncResult(productId: string, countryId: string, payload: SyncResult) {
    setProducts(prev => prev.map(product => {
      if (product.id !== productId) return product;
      const countries = (product.countries || []).map(country => (
        country.id === countryId
          ? {
              ...country,
              creatorCount: Number(payload.creator_count) || 0,
              materialCount: Number(payload.material_count) || 0,
              reelFarmSyncedAt: payload.synced_at || country.reelFarmSyncedAt
            }
          : country
      ));
      return {
        ...product,
        countries,
        creatorCount: countries.reduce((sum, country) => sum + (Number(country.creatorCount) || 0), 0),
        materialCount: countries.reduce((sum, country) => sum + (Number(country.materialCount) || 0), 0)
      };
    }));
  }

  async function syncCountry() {
    if (!selectedProduct || !selectedCountry) return;
    const prefix = buildCountryAutomationPrefix(selectedProduct, selectedCountry);
    setSyncPrefix(`country:${selectedCountry.id}`);
    try {
      const payload = await api.syncCountry({
        prefix,
        product_id: selectedProduct.id,
        country_id: selectedCountry.id,
        product_code: getProductReelFarmCode(selectedProduct),
        country_code: getCountryReelFarmCode(selectedCountry)
      });
      applySyncResult(selectedProduct.id, selectedCountry.id, payload);
      resetReelFarmState({ includeResults: false });
      await loadAccounts(selectedProduct, selectedCountry, true);
      await loadProductKpis(selectedProduct);
      await loadCountryKpis(selectedProduct, selectedCountry);
      onStatus(`当前区同步完成：${payload.creator_count} 个账号，${payload.material_count} 个素材`);
    } catch (error: any) {
      onStatus(error?.message || 'ReelFarm 同步失败', true);
    } finally {
      setSyncPrefix('');
    }
  }

  async function syncProductCountries(product: Product) {
    const countries = product.countries || [];
    if (!countries.length || syncProductId) return;
    setSyncProductId(product.id);
    resetReelFarmState();
    let failed = 0;
    try {
      for (let index = 0; index < countries.length; index += 1) {
        const country = countries[index];
        setSyncPrefix(`country:${country.id}`);
        onStatus(`同步 ${product.name}：${index + 1}/${countries.length} ${country.name}`);
        try {
          const payload = await api.syncCountry({
            prefix: buildCountryAutomationPrefix(product, country),
            product_id: product.id,
            country_id: country.id,
            product_code: getProductReelFarmCode(product),
            country_code: getCountryReelFarmCode(country)
          });
          applySyncResult(product.id, country.id, payload);
        } catch (error: any) {
          failed += 1;
          onStatus(`${product.name} · ${country.name} 同步失败：${error?.message || '未知错误'}`, true);
        }
        if (index < countries.length - 1) await wait(1400);
      }
      await loadProductKpis(product);
      if (selectedProductId === product.id && page === 'country') {
        await loadCountryKpis(selectedProduct, selectedCountry);
        await loadAccounts(selectedProduct, selectedCountry, true);
      }
      onStatus(failed ? `${product.name} 同步完成：${failed} 个地区失败` : `${product.name} 已同步完成`, Boolean(failed));
    } finally {
      setSyncPrefix('');
      setSyncProductId('');
    }
  }

  async function syncCloneProductCountries(product: Product) {
    const countries = product.countries || [];
    if (!countries.length || syncProductId) return;
    setSyncProductId(product.id);
    let failed = 0;
    try {
      for (let index = 0; index < countries.length; index += 1) {
        const country = countries[index];
        setSyncPrefix(`clone:${country.id}`);
        onStatus(`同步 Clone ${product.name}：${index + 1}/${countries.length} ${country.name}`);
        try {
          await api.syncMuseonCloneCountry({
            product_id: product.id,
            country_id: country.id,
            product_code: getProductReelFarmCode(product),
            country_code: getCountryReelFarmCode(country)
          });
        } catch (error: any) {
          failed += 1;
          onStatus(`Clone ${product.name} · ${country.name} 同步失败：${error?.message || '未知错误'}`, true);
        }
        if (index < countries.length - 1) await wait(900);
      }
      await loadCloneProductData(products);
      onStatus(failed ? `Clone ${product.name} 同步完成：${failed} 个地区失败` : `Clone ${product.name} 已同步完成`, Boolean(failed));
    } finally {
      setSyncPrefix('');
      setSyncProductId('');
    }
  }

  async function syncAllCountries() {
    if (syncAllRunning) return;
    const jobs = products.flatMap(product => (product.countries || []).map(country => ({ product, country })));
    if (!jobs.length) return;
    setSyncAllRunning(true);
    resetReelFarmState();
    let failed = 0;
    try {
      for (let index = 0; index < jobs.length; index += 1) {
        const { product, country } = jobs[index];
        const progress = `${index + 1}/${jobs.length}`;
        setSyncAllProgress(progress);
        onStatus(`同步全部中：${progress} ${product.name} · ${country.name}`);
        setSyncPrefix(`country:${country.id}`);
        try {
          const payload = await api.syncCountry({
            prefix: buildCountryAutomationPrefix(product, country),
            product_id: product.id,
            country_id: country.id,
            product_code: getProductReelFarmCode(product),
            country_code: getCountryReelFarmCode(country)
          });
          applySyncResult(product.id, country.id, payload);
        } catch (error: any) {
          failed += 1;
          onStatus(`${product.name} · ${country.name} 同步失败：${error?.message || '未知错误'}`, true);
        }
        if (index < jobs.length - 1) await wait(1800);
      }
      onStatus(failed ? `同步全部完成：${failed} 个地区失败，可单独重试` : '同步全部完成', Boolean(failed));
      await Promise.all(products.map(product => loadProductKpis(product)));
      if (page === 'country') await loadCountryKpis(selectedProduct, selectedCountry);
      if (page === 'country') {
        await loadAccounts(selectedProduct, selectedCountry, true);
      }
    } finally {
      setSyncPrefix('');
      setSyncAllProgress('');
      setSyncAllRunning(false);
    }
  }

  return {
    syncPrefix,
    syncProductId,
    syncAllRunning,
    syncAllProgress,
    syncCountry,
    syncProductCountries,
    syncCloneProductCountries,
    syncAllCountries
  };
}
