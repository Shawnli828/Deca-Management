'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Product } from '@/lib/types';
import { formatNumber } from '@/lib/utils';
import {
  buildCountrySections,
  cloudProductsFrom,
  geeLarkKey,
  productCountryPairs,
  stateLabels,
  type GeeLarkMapPayload,
  type GeeLarkPayloadMap,
  type IpGroup,
  type PhoneSlot
} from '@/components/CloudPhoneMapHelpers';

export type SelectedCloudPhoneSlot = PhoneSlot & { ipGroup: IpGroup };

export function useCloudPhoneMap(products: Product[]) {
  const [geeLarkPayloads, setGeeLarkPayloads] = useState<GeeLarkPayloadMap>({});
  const [geeLarkLoading, setGeeLarkLoading] = useState(false);
  const [geeLarkError, setGeeLarkError] = useState('');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');

  const geeLarkPairs = useMemo(() => productCountryPairs(products), [products]);
  const cloudProducts = useMemo(() => cloudProductsFrom(products, geeLarkPayloads), [products, geeLarkPayloads]);
  const defaultProductId = cloudProducts.find(product => product.code === 'DB')?.id || '';
  const selectedProduct = cloudProducts.find(product => product.id === (selectedProductId || defaultProductId)) || cloudProducts[0];

  const selectedSlot = selectedProduct?.ipGroups
    .flatMap(ipGroup => ipGroup.slots.map(slot => ({ ...slot, ipGroup })))
    .find(slot => slot.id === selectedSlotId) as SelectedCloudPhoneSlot | undefined;

  const totals = selectedProduct?.ipGroups.reduce((sum, ipGroup) => ({
    ipGroups: sum.ipGroups + 1,
    phones: sum.phones + ipGroup.phoneCount,
    active: sum.active + ipGroup.activeCount,
    warnings: sum.warnings + ipGroup.slots.filter(slot => slot.state === 'warming' || slot.state === 'offline').length
  }), { ipGroups: 0, phones: 0, active: 0, warnings: 0 }) || { ipGroups: 0, phones: 0, active: 0, warnings: 0 };

  const countrySections = useMemo(() => buildCountrySections(selectedProduct?.ipGroups || []), [selectedProduct]);
  const liveTotals = useMemo(() => Object.values(geeLarkPayloads).reduce((sum, payload) => ({
    pairs: sum.pairs + 1,
    groups: sum.groups + Number(payload.group_count || 0),
    phones: sum.phones + Number(payload.phone_count || 0)
  }), { pairs: 0, groups: 0, phones: 0 }), [geeLarkPayloads]);

  const liveLabel = liveTotals.groups
    ? `GeeLark 已接入 · ${liveTotals.pairs} 区 / ${liveTotals.groups} 组 / ${formatNumber(liveTotals.phones)} 台`
    : 'GeeLark 接入预览';
  const selectedPhoneTitle = selectedSlot
    ? (selectedSlot.serialNo ? `No. ${selectedSlot.serialNo}` : selectedSlot.label)
    : '点击手机查看详情';

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
