import { formatNumber } from '@/lib/utils';
import type { CloudProduct, CountrySection, GeeLarkPayloadMap, IpGroup, PhoneSlot } from './cloudPhoneTypes';

export { stateLabels } from './cloudPhoneConstants';
export { cloudProductsFrom, geeLarkKey, productCountryPairs } from './cloudPhoneData';

export type {
  CloudProduct,
  CountrySection,
  GeeLarkGroup,
  GeeLarkMapPayload,
  GeeLarkPayload,
  GeeLarkPayloadMap,
  GeeLarkPhone,
  IpGroup,
  PhoneSlot,
  PhoneState
} from './cloudPhoneTypes';

export type SelectedCloudPhoneSlot = PhoneSlot & { ipGroup: IpGroup };

export type CloudPhoneTotals = {
  ipGroups: number;
  phones: number;
  active: number;
  warnings: number;
};

export type GeeLarkLiveTotals = {
  pairs: number;
  groups: number;
  phones: number;
};

export const emptyCloudPhoneTotals: CloudPhoneTotals = {
  ipGroups: 0,
  phones: 0,
  active: 0,
  warnings: 0
};

export function selectCloudProduct(cloudProducts: CloudProduct[], selectedProductId: string) {
  const defaultProductId = cloudProducts.find(product => product.code === 'DB')?.id || '';
  return cloudProducts.find(product => product.id === (selectedProductId || defaultProductId)) || cloudProducts[0];
}

export function selectCloudPhoneSlot(product: CloudProduct | undefined, selectedSlotId: string): SelectedCloudPhoneSlot | undefined {
  return product?.ipGroups
    .flatMap(ipGroup => ipGroup.slots.map(slot => ({ ...slot, ipGroup })))
    .find(slot => slot.id === selectedSlotId);
}

export function summarizeIpGroups(ipGroups: IpGroup[] = []): CloudPhoneTotals {
  return ipGroups.reduce((sum, ipGroup) => ({
    ipGroups: sum.ipGroups + 1,
    phones: sum.phones + ipGroup.phoneCount,
    active: sum.active + ipGroup.activeCount,
    warnings: sum.warnings + ipGroup.slots.filter(slot => slot.state === 'warming' || slot.state === 'offline').length
  }), emptyCloudPhoneTotals);
}

export function summarizeGeeLarkPayloads(geeLarkPayloads: GeeLarkPayloadMap): GeeLarkLiveTotals {
  return Object.values(geeLarkPayloads).reduce((sum, payload) => ({
    pairs: sum.pairs + 1,
    groups: sum.groups + Number(payload.group_count || 0),
    phones: sum.phones + Number(payload.phone_count || 0)
  }), { pairs: 0, groups: 0, phones: 0 });
}

export function formatGeeLarkLiveLabel(liveTotals: GeeLarkLiveTotals) {
  return liveTotals.groups
    ? `GeeLark 已接入 · ${liveTotals.pairs} 区 / ${liveTotals.groups} 组 / ${formatNumber(liveTotals.phones)} 台`
    : 'GeeLark 接入预览';
}

export function formatSelectedPhoneTitle(selectedSlot: SelectedCloudPhoneSlot | undefined) {
  return selectedSlot
    ? (selectedSlot.serialNo ? `No. ${selectedSlot.serialNo}` : selectedSlot.label)
    : '点击手机查看详情';
}

export function buildCountrySections(ipGroups: IpGroup[]): CountrySection[] {
  const sections = new Map<string, CountrySection>();
  ipGroups.forEach(ipGroup => {
    const code = ipGroup.code || 'UN';
    const countryName = ipGroup.countryName || code;
    const key = `${code}:${countryName}`;
    const current = sections.get(key) || {
      id: key,
      code,
      countryName,
      ipGroups: [],
      phoneCount: 0,
      activeCount: 0,
      warningCount: 0
    };
    current.ipGroups.push(ipGroup);
    current.phoneCount += ipGroup.phoneCount;
    current.activeCount += ipGroup.activeCount;
    current.warningCount += ipGroup.slots.filter(slot => slot.state === 'warming' || slot.state === 'offline').length;
    sections.set(key, current);
  });
  return [...sections.values()].sort((left, right) => left.code.localeCompare(right.code));
}

export function compactIpGroupName(name: string, countryCode: string, productCode: string) {
  const parts = name.split('-').filter(Boolean);
  const countryIndex = parts.findIndex(part => part.toUpperCase() === countryCode.toUpperCase());
  let productIndex = -1;
  for (let index = parts.length - 1; index >= 0; index -= 1) {
    if (parts[index].toUpperCase() === productCode.toUpperCase()) {
      productIndex = index;
      break;
    }
  }
  if (countryIndex !== -1 && productIndex > countryIndex + 1) {
    return parts.slice(countryIndex + 1, productIndex).join('-');
  }
  return name.replace(/^Zhan-/i, '').replace(new RegExp(`-${productCode}$`, 'i'), '') || name;
}
