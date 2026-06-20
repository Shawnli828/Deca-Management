import type { Country } from '@/lib/types';
import type { PhoneState } from './cloudPhoneTypes';

export const fallbackCountries: Country[] = [
  { id: 'ge', name: 'Germany', reelFarmCode: 'GE', creatorCount: 18 },
  { id: 'us', name: 'United States', reelFarmCode: 'US', creatorCount: 24 },
  { id: 'fr', name: 'France', reelFarmCode: 'FR', creatorCount: 12 }
];

export const countryNamesByCode: Record<string, string> = {
  AT: 'Austria',
  AU: 'Australia',
  BR: 'Brazil',
  CA: 'Canada',
  CN: 'China',
  DE: 'Germany',
  FR: 'France',
  GB: 'United Kingdom',
  GE: 'Germany',
  IN: 'India',
  IT: 'Italy',
  JP: 'Japan',
  KR: 'South Korea',
  UK: 'United Kingdom',
  US: 'United States'
};

export const stateLabels: Record<PhoneState, string> = {
  ready: '可用',
  running: '运行中',
  warming: '预热中',
  offline: '离线',
  empty: '空位'
};
