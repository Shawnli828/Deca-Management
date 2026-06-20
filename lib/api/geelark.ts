import type { GeeLarkMapPayload } from '@/lib/domain/cloudPhoneTypes';
import { apiFetch, withQuery } from './client';

export type GeeLarkPair = {
  productCode: string;
  countryCode: string;
};

export const geelarkApi = {
  phonesMap: (pairs: GeeLarkPair[], init?: RequestInit) => {
    const pairQuery = pairs
      .map(pair => `${pair.productCode}:${pair.countryCode}`)
      .join(',');
    return apiFetch<GeeLarkMapPayload>(
      withQuery('/api/geelark/phones-map', new URLSearchParams({ pairs: pairQuery })),
      init,
      'GeeLark API failed'
    );
  }
};
