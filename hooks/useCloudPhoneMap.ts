'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Product } from '@/lib/types';
import {
  buildCountrySections,
  cloudProductsFrom,
  formatGeeLarkLiveLabel,
  formatSelectedPhoneTitle,
  geeLarkKey,
  productCountryPairs,
  selectCloudPhoneSlot,
  selectCloudProduct,
  summarizeGeeLarkPayloads,
  summarizeIpGroups,
  type GeeLarkMapPayload,
  type GeeLarkPayloadMap,
  type SelectedCloudPhoneSlot
} from '@/components/CloudPhoneMapHelpers';

export type { SelectedCloudPhoneSlot };

export function useCloudPhoneMap(products: Product[]) {
  const [geeLarkPayloads, setGeeLarkPayloads] = useState<GeeLarkPayloadMap>({});
  const [geeLarkLoading, setGeeLarkLoading] = useState(false);
  const [geeLarkError, setGeeLarkError] = useState('');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');

  const geeLarkPairs = useMemo(() => productCountryPairs(products), [products]);
  const cloudProducts = useMemo(() => cloudProductsFrom(products, geeLarkPayloads), [products, geeLarkPayloads]);
  const selectedProduct = useMemo(() => selectCloudProduct(cloudProducts, selectedProductId), [cloudProducts, selectedProductId]);
  const selectedSlot = useMemo(() => selectCloudPhoneSlot(selectedProduct, selectedSlotId), [selectedProduct, selectedSlotId]);
  const totals = useMemo(() => summarizeIpGroups(selectedProduct?.ipGroups), [selectedProduct]);

  const countrySections = useMemo(() => buildCountrySections(selectedProduct?.ipGroups || []), [selectedProduct]);
  const liveTotals = useMemo(() => summarizeGeeLarkPayloads(geeLarkPayloads), [geeLarkPayloads]);

  const liveLabel = formatGeeLarkLiveLabel(liveTotals);
  const selectedPhoneTitle = formatSelectedPhoneTitle(selectedSlot);

  useEffect(() => {
    let cancelled = false;
    if (!geeLarkPairs.length) return () => {
      cancelled = true;
    };
    setGeeLarkLoading(true);
    setGeeLarkError('');
    const query = geeLarkPairs
      .map(pair => `${encodeURIComponent(pair.productCode)}:${encodeURIComponent(pair.countryCode)}`)
      .join(',');
    fetch(`/api/geelark/phones-map?pairs=${query}`)
      .then(async response => {
        const text = await response.text();
        let payload: GeeLarkMapPayload | { error?: string };
        try {
          payload = JSON.parse(text);
        } catch {
          throw new Error(text.slice(0, 220) || 'GeeLark response is not JSON');
        }
        if (!response.ok || !('ok' in payload) || !payload.ok) {
          const apiError = 'error' in payload ? payload.error : '';
          throw new Error(apiError || 'GeeLark API failed');
        }
        const nextPayloads: GeeLarkPayloadMap = {};
        (payload as GeeLarkMapPayload).items?.forEach(item => {
          const productCode = String(item.filters?.product_code || '').toUpperCase();
          const countryCode = String(item.filters?.country_code || '').toUpperCase();
          if (productCode && countryCode) {
            nextPayloads[geeLarkKey(productCode, countryCode)] = item;
          }
        });
        if (!cancelled) setGeeLarkPayloads(nextPayloads);
      })
      .catch(error => {
        if (!cancelled) setGeeLarkError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (!cancelled) setGeeLarkLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [geeLarkPairs]);

  return {
    cloudProducts,
    countrySections,
    geeLarkError,
    geeLarkLoading,
    liveLabel,
    selectedPhoneTitle,
    selectedProduct,
    selectedProductId,
    selectedSlot,
    selectedSlotId,
    setSelectedProductId,
    setSelectedSlotId,
    totals
  };
}
