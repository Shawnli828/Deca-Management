'use client';

import { useEffect, useMemo, useState } from 'react';
import { api, getErrorMessage } from '@/lib/api';
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
  type GeeLarkPayloadMap,
  type SelectedCloudPhoneSlot
} from '@/lib/domain/cloudPhoneMap';

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
    const controller = new AbortController();
    if (!geeLarkPairs.length) return () => {
      cancelled = true;
      controller.abort();
    };
    setGeeLarkLoading(true);
    setGeeLarkError('');
    api.phonesMap(geeLarkPairs, { signal: controller.signal })
      .then(payload => {
        const nextPayloads: GeeLarkPayloadMap = {};
        payload.items?.forEach(item => {
          const productCode = String(item.filters?.product_code || '').toUpperCase();
          const countryCode = String(item.filters?.country_code || '').toUpperCase();
          if (productCode && countryCode) {
            nextPayloads[geeLarkKey(productCode, countryCode)] = item;
          }
        });
        if (!cancelled) setGeeLarkPayloads(nextPayloads);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (!cancelled) setGeeLarkError(getErrorMessage(error, 'GeeLark API failed'));
      })
      .finally(() => {
        if (!cancelled) setGeeLarkLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
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
