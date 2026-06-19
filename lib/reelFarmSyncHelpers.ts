import type { Product } from './types';

export const SYNC_PRODUCT_COUNTRY_DELAY_MS = 1400;
export const SYNC_CLONE_COUNTRY_DELAY_MS = 900;
export const SYNC_ALL_COUNTRY_DELAY_MS = 1800;

export type CountrySyncResult = {
  creator_count?: number;
  material_count?: number;
  synced_at?: string;
};

export function wait(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function applyCountrySyncPayload(
  products: Product[],
  productId: string,
  countryId: string,
  payload: CountrySyncResult
) {
  return products.map(product => {
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
  });
}
