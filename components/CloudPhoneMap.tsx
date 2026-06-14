'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Country, Product } from '@/lib/types';
import { formatNumber, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

type PhoneState = 'ready' | 'running' | 'warming' | 'offline' | 'empty';

type PhoneSlot = {
  id: string;
  label: string;
  state: PhoneState;
  account?: string;
  serialName?: string;
  serialNo?: string;
  groupName?: string;
  countryName?: string;
  timeZone?: string;
  deviceModel?: string;
  statusCode?: number | string | null;
  rpaStatus?: number | string | null;
  tags?: string[];
};

type IpGroup = {
  id: string;
  name: string;
  code: string;
  countryName: string;
  source?: string;
  phoneCount: number;
  activeCount: number;
  slots: PhoneSlot[];
};

type CloudProduct = {
  id: string;
  name: string;
  code: string;
  logo?: string;
  folder?: string;
  ipGroups: IpGroup[];
};

type CountrySection = {
  id: string;
  code: string;
  countryName: string;
  ipGroups: IpGroup[];
  phoneCount: number;
  activeCount: number;
  warningCount: number;
};

type GeeLarkPhone = {
  id: string;
  serialName?: string;
  serialNo?: string;
  groupName?: string;
  countryName?: string;
  timeZone?: string;
  deviceModel?: string;
  status?: number | string | null;
  rpaStatus?: number | string | null;
  tags?: string[];
};

type GeeLarkGroup = {
  id: string;
  name: string;
  productCode: string;
  countryCode: string;
  countryName?: string;
  phones: GeeLarkPhone[];
};

type GeeLarkPayload = {
  ok: boolean;
  phone_count: number;
  group_count: number;
  filters?: {
    product_code?: string;
    country_code?: string;
  };
  groups: GeeLarkGroup[];
};

type GeeLarkPayloadMap = Record<string, GeeLarkPayload>;

type GeeLarkMapPayload = {
  ok: boolean;
  phone_count: number;
  group_count: number;
  items: GeeLarkPayload[];
};

const fallbackCountries: Country[] = [
  { id: 'ge', name: 'Germany', reelFarmCode: 'GE', creatorCount: 18 },
  { id: 'us', name: 'United States', reelFarmCode: 'US', creatorCount: 24 },
  { id: 'fr', name: 'France', reelFarmCode: 'FR', creatorCount: 12 }
];

const countryNamesByCode: Record<string, string> = {
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

const stateLabels: Record<PhoneState, string> = {
  ready: '可用',
  running: '运行中',
  warming: '预热中',
  offline: '离线',
  empty: '空位'
};

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

function geeLarkKey(productCode: string, countryCode: string) {
  return `${productCode.toUpperCase()}:${countryCode.toUpperCase()}`;
}

function sourceProductsForCloud(products: Product[]) {
  return products.length ? products : [
    { id: 'demo-db', name: 'DeenBack', reelFarmCode: 'DB', countries: fallbackCountries, creatorCount: 54 },
    { id: 'demo-dl', name: 'Delust', reelFarmCode: 'DL', countries: fallbackCountries.slice(0, 2), creatorCount: 34 },
    { id: 'demo-dm', name: 'Demi', reelFarmCode: 'DM', countries: fallbackCountries.slice(1, 3), creatorCount: 20 }
  ];
}

function productCountryPairs(products: Product[]) {
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

function buildCountrySections(ipGroups: IpGroup[]): CountrySection[] {
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

function compactIpGroupName(name: string, countryCode: string, productCode: string) {
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

function cloudProductsFrom(products: Product[], geeLarkPayloads: GeeLarkPayloadMap): CloudProduct[] {
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

function PhoneGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="7" y="2.8" width="10" height="18.4" rx="2.4" />
      <path d="M10.4 5.4h3.2" />
      <path d="M11 18.3h2" />
    </svg>
  );
}

export function CloudPhoneMap({ products }: { products: Product[] }) {
  const [geeLarkPayloads, setGeeLarkPayloads] = useState<GeeLarkPayloadMap>({});
  const [geeLarkLoading, setGeeLarkLoading] = useState(false);
  const [geeLarkError, setGeeLarkError] = useState('');
  const cloudProducts = useMemo(() => cloudProductsFrom(products, geeLarkPayloads), [products, geeLarkPayloads]);
  const defaultProductId = cloudProducts.find(product => product.code === 'DB')?.id || '';
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const geeLarkPairs = useMemo(() => productCountryPairs(products), [products]);

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

  const selectedProduct = cloudProducts.find(product => product.id === (selectedProductId || defaultProductId)) || cloudProducts[0];
  const selectedSlot = selectedProduct?.ipGroups
    .flatMap(ipGroup => ipGroup.slots.map(slot => ({ ...slot, ipGroup })))
    .find(slot => slot.id === selectedSlotId);
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

  return (
    <section className="cloud-phone-page">
      <header className="cloud-phone-hero">
        <div>
          <p className="dashboard-kicker">GeeLark Cloud Phone</p>
          <h1>云手机分布图</h1>
          <p>按「产品 → 国家 → IP 分组 → 云手机」查看 GeeLark 资产。真实命名里 US-DB、DB-US 这类顺序都会识别到对应产品和地区。</p>
        </div>
        <div className="cloud-phone-status">
          <span>{geeLarkLoading ? '正在读取 GeeLark' : liveLabel}</span>
          <strong>{formatNumber(totals.phones)}</strong>
          <small>台云手机</small>
        </div>
      </header>

      {geeLarkError ? (
        <div className="cloud-inline-warning">
          GeeLark 接口暂未返回真实数据：{geeLarkError}。当前页面先显示产品结构预览；配置 GEELARK_API_TOKEN 后会自动读取所有产品和地区。
        </div>
      ) : null}

      <div className="cloud-phone-layout">
        <aside className="cloud-product-rail" aria-label="产品选择">
          <div className="cloud-panel-title">
            <strong>产品</strong>
            <span>{cloudProducts.length} 个产品</span>
          </div>
          {cloudProducts.map(product => {
            const phoneCount = product.ipGroups.reduce((sum, ipGroup) => sum + ipGroup.phoneCount, 0);
            const active = selectedProduct?.id === product.id;
            return (
              <button
                className={`cloud-product-card ${active ? 'active' : ''}`}
                type="button"
                onClick={() => {
                  setSelectedProductId(product.id);
                  setSelectedSlotId('');
                }}
                key={product.id}
              >
                <span className="cloud-product-logo">
                  {product.logo ? <img src={product.logo} alt="" /> : product.code.slice(0, 2)}
                </span>
                <span>
                  <strong>{product.name}</strong>
                  <small>{product.folder} · {product.ipGroups.length} 个 IP 分组 · {formatNumber(phoneCount)} 台手机</small>
                </span>
              </button>
            );
          })}
        </aside>

        <section className="cloud-seat-map">
          <div className="cloud-seat-toolbar">
            <div>
              <span>{selectedProduct?.code}</span>
              <h2>{selectedProduct?.name} IP 分组视图</h2>
            </div>
            <div className="cloud-seat-summary">
              <span><b>{totals.ipGroups}</b> IP 分组</span>
              <span><b>{formatNumber(totals.active)}</b> 可用手机</span>
              <span><b>{formatNumber(totals.warnings)}</b> 待检查</span>
            </div>
          </div>

          <div className="cloud-country-stack">
            {countrySections.length ? countrySections.map(section => (
              <section className="cloud-country-block" key={section.id}>
                <div className="cloud-country-head">
                  <div>
                    <span className="cloud-env-code cloud-country-code">{section.code}</span>
                    <div>
                      <strong>{section.countryName}</strong>
                      <small>{section.ipGroups.length} 个分组 · {formatNumber(section.phoneCount)} 台手机 · {formatNumber(section.activeCount)} 台可用</small>
                    </div>
                  </div>
                  <span className="cloud-country-health">{section.warningCount ? `${section.warningCount} 台待检查` : '状态正常'}</span>
                </div>

                <div className="cloud-ip-group-grid">
                  {section.ipGroups.map(ipGroup => {
                    const displayName = compactIpGroupName(ipGroup.name, ipGroup.code, selectedProduct?.code || '');
                    return (
                      <article className="cloud-ip-group-card" key={ipGroup.id}>
                        <div className="cloud-ip-group-head">
                          <div>
                            <strong>{displayName}</strong>
                            <small>{ipGroup.name}</small>
                          </div>
                          <span className="cloud-env-health">{ipGroup.activeCount}/{ipGroup.phoneCount}</span>
                        </div>
                        <div className="cloud-phone-grid" aria-label={`${ipGroup.name} 云手机`}>
                          {ipGroup.slots.map(slot => (
                            <button
                              className={`cloud-phone-slot ${slot.state} ${selectedSlotId === slot.id ? 'selected' : ''}`}
                              type="button"
                              title={`${slot.label} · ${stateLabels[slot.state]}${slot.tags?.length ? ` · ${slot.tags.join(', ')}` : ''}`}
                              key={slot.id}
                              onClick={() => setSelectedSlotId(slot.id)}
                            >
                              <PhoneGlyph />
                              <span>{slot.label}</span>
                              {slot.tags?.[0] ? <em>{slot.tags[0]}</em> : null}
                            </button>
                          ))}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            )) : (
              <div className="cloud-empty-state">
                当前产品暂未匹配到 GeeLark 分组。请确认分组名里包含产品 code 和国家 code，例如 GE-DB 或 DB-GE。
              </div>
            )}
          </div>
        </section>

        <aside className="cloud-inspector">
          <div className="cloud-inspector-card">
            <span className="cloud-mini-label">当前产品</span>
            <h3>{selectedProduct?.name}</h3>
            <p>{selectedProduct?.code} · {selectedProduct?.folder}</p>
            <dl>
              <div><dt>IP 分组</dt><dd>{totals.ipGroups}</dd></div>
              <div><dt>云手机</dt><dd>{formatNumber(totals.phones)}</dd></div>
              <div><dt>可用</dt><dd>{formatNumber(totals.active)}</dd></div>
              <div><dt>待检查</dt><dd>{formatNumber(totals.warnings)}</dd></div>
            </dl>
          </div>
          <div className="cloud-inspector-card">
            <span className="cloud-mini-label">选中手机</span>
            {selectedSlot ? (
              <>
                <h3>{selectedSlot.serialNo ? `No. ${selectedSlot.serialNo}` : selectedSlot.label}</h3>
                <p>{selectedSlot.groupName || selectedSlot.ipGroup.name}</p>
                <dl>
                  <div><dt>国家</dt><dd>{selectedSlot.countryName || selectedSlot.ipGroup.countryName}</dd></div>
                  <div><dt>状态</dt><dd>{stateLabels[selectedSlot.state]}</dd></div>
                  <div><dt>RPA</dt><dd>{selectedSlot.rpaStatus ?? '—'}</dd></div>
                  <div><dt>标签</dt><dd>{selectedSlot.tags?.join(' · ') || '—'}</dd></div>
                </dl>
              </>
            ) : (
              <p>点击中间任意手机后，这里会展示 GeeLark 分组、国家、serialNo、运行状态和 tags。</p>
            )}
          </div>
          <div className="cloud-inspector-card">
            <span className="cloud-mini-label">状态说明</span>
            {(['running', 'ready', 'warming', 'offline', 'empty'] as PhoneState[]).map(state => (
              <div className="cloud-legend-row" key={state}>
                <span className={`cloud-dot ${state}`} />
                <strong>{stateLabels[state]}</strong>
              </div>
            ))}
          </div>
          <div className="cloud-inspector-note">
            下一步可以把 GeeLark 数据落到数据库：product_code、country_code、group_name、phone_id、serial_no、status、tags、synced_at。
          </div>
        </aside>
      </div>
    </section>
  );
}
