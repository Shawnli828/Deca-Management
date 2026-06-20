import type { Product } from '@/lib/types';
import { getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';
import { countryNamesByCode, fallbackCountries } from './cloudPhoneConstants';
import type { CloudProduct, GeeLarkPayload, GeeLarkPayloadMap, IpGroup, PhoneSlot, PhoneState } from './cloudPhoneTypes';

function slotState(seed: number, index: number): PhoneState {
  const score = (seed * 17 + index * 11) % 23;
  if (score === 0) return 'offline';
  if (score <= 3) return 'warming';
  if (score <= 12) return 'running';
  return 'ready';
}

function statusToState(status: number | string | null | undefined, rpaStatus: number | string | null | undefined): PhoneState {
  const statusText = String(status ?? '');
  const rpaText = String(rpaStatus ?? '');
  if (statusText === '0' || statusText.toLowerCase() === 'offline') return 'offline';
  if (rpaText !== '' && rpaText !== '0') return 'running';
  if (statusText === '2') return 'ready';
  if (statusText === '1') return 'warming';
  return 'ready';
}

function countryNameForCode(code?: string, fallback?: string) {
  const cleanCode = String(code || '').toUpperCase();
  return fallback || countryNamesByCode[cleanCode] || cleanCode || 'Unknown';
}

function buildSlots(productCode: string, countryCode: string, count: number): PhoneSlot[] {
  const capacity = Math.max(12, Math.min(40, Math.ceil(count / 4) * 4 || 12));
  const seed = [...`${productCode}${countryCode}`].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return Array.from({ length: capacity }, (_, index) => {
    const active = index < count;
    const state = active ? slotState(seed, index) : 'empty';
    return {
      id: `${productCode}-${countryCode}-${index}`,
      label: `${countryCode}${String(index + 1).padStart(2, '0')}`,
      state,
      account: active ? `gk-${productCode.toLowerCase()}-${countryCode.toLowerCase()}-${String(index + 1).padStart(2, '0')}` : undefined
    };
  });
}

function geGroupSortValue(name: string) {
  return name.split(/(\d+)/).map(part => (/^\d+$/.test(part) ? Number(part) : part.toLowerCase()));
}

function buildGeeLarkGroups(payload?: GeeLarkPayload | null): IpGroup[] {
  if (!payload?.ok || !payload.groups?.length) return [];
  return [...payload.groups]
    .sort((left, right) => {
      const a = geGroupSortValue(left.name);
      const b = geGroupSortValue(right.name);
      return String(a).localeCompare(String(b), undefined, { numeric: true });
    })
    .map(group => {
      const countryName = countryNameForCode(group.countryCode, group.countryName);
      const slots = group.phones.map((phone, index) => {
        const label = phone.serialName || phone.serialNo || String(index + 1);
        return {
          id: phone.id || `${group.name}:${index}`,
          label,
          state: statusToState(phone.status, phone.rpaStatus),
          serialName: phone.serialName,
          serialNo: phone.serialNo,
          groupName: group.name,
          countryName: countryNameForCode(group.countryCode, phone.countryName || group.countryName),
          timeZone: phone.timeZone,
          deviceModel: phone.deviceModel,
          statusCode: phone.status,
          rpaStatus: phone.rpaStatus,
          tags: phone.tags || []
        };
      });
      return {
        id: `geelark:${group.name}`,
        name: group.name,
        code: group.countryCode || 'GE',
        countryName,
        source: 'GeeLark',
        phoneCount: slots.length,
        activeCount: slots.filter(slot => slot.state !== 'offline' && slot.state !== 'empty').length,
        slots
      };
    });
}

export function geeLarkKey(productCode: string, countryCode: string) {
  return `${productCode.toUpperCase()}:${countryCode.toUpperCase()}`;
}

function sourceProductsForCloud(products: Product[]) {
  return products.length ? products : [
    { id: 'demo-db', name: 'DeenBack', reelFarmCode: 'DB', countries: fallbackCountries, creatorCount: 54 },
    { id: 'demo-dl', name: 'Delust', reelFarmCode: 'DL', countries: fallbackCountries.slice(0, 2), creatorCount: 34 },
    { id: 'demo-dm', name: 'Demi', reelFarmCode: 'DM', countries: fallbackCountries.slice(1, 3), creatorCount: 20 }
  ];
}

export function productCountryPairs(products: Product[]) {
  const pairs = new Map<string, { productCode: string; countryCode: string }>();
  sourceProductsForCloud(products).forEach(product => {
    const productCode = getProductReelFarmCode(product) || product.name.slice(0, 2).toUpperCase();
    const countries = product.countries?.length ? product.countries : fallbackCountries.slice(0, 2);
    countries.forEach(country => {
      const countryCode = getCountryReelFarmCode(country) || country.name.slice(0, 2).toUpperCase();
      pairs.set(geeLarkKey(productCode, countryCode), { productCode, countryCode });
    });
  });
  return [...pairs.values()];
}

export function cloudProductsFrom(products: Product[], geeLarkPayloads: GeeLarkPayloadMap): CloudProduct[] {
  const sourceProducts = sourceProductsForCloud(products);
  const hasGeeLarkPayloads = Object.keys(geeLarkPayloads).length > 0;

  return sourceProducts.map((product, productIndex) => {
    const productCode = getProductReelFarmCode(product) || product.name.slice(0, 2).toUpperCase();
    const countries = product.countries?.length ? product.countries : fallbackCountries.slice(0, 2);
    const liveGroups = countries.flatMap(country => {
      const countryCode = getCountryReelFarmCode(country) || country.name.slice(0, 2).toUpperCase();
      return buildGeeLarkGroups(geeLarkPayloads[geeLarkKey(productCode, countryCode)]);
    });

    const ipGroups = hasGeeLarkPayloads
      ? liveGroups
      : countries.map((country, countryIndex) => {
        const countryCode = getCountryReelFarmCode(country) || country.name.slice(0, 2).toUpperCase();
        const fallbackCount = 10 + productIndex * 4 + countryIndex * 3;
        const phoneCount = Math.max(4, Math.min(36, Number(country.creatorCount || country.automationCount || fallbackCount)));
        const slots = buildSlots(productCode, countryCode, phoneCount);
        return {
          id: `${product.id}:${country.id}`,
          name: `${country.name} IP 分组`,
          code: countryCode,
          countryName: country.name,
          source: 'Preview',
          phoneCount,
          activeCount: slots.filter(slot => slot.state === 'running' || slot.state === 'ready').length,
          slots
        };
      });

    return {
      id: product.id,
      name: product.name || '未命名产品',
      code: productCode,
      logo: product.logo,
      folder: product.folder || product.owner_type || '甲方',
      ipGroups
    };
  });
}
