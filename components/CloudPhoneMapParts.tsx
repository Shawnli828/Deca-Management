'use client';

import { formatNumber } from '@/lib/utils';
import {
  compactIpGroupName,
  stateLabels,
  type CloudPhoneTotals,
  type CloudProduct,
  type CountrySection,
  type SelectedCloudPhoneSlot
} from './CloudPhoneMapHelpers';

function PhoneGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="7" y="2.8" width="10" height="18.4" rx="2.4" />
      <path d="M10.4 5.4h3.2" />
      <path d="M11 18.3h2" />
    </svg>
  );
}

type CloudProductRailProps = {
  products: CloudProduct[];
  selectedProductId?: string;
  onSelectProduct: (productId: string) => void;
};

export function CloudProductRail({ products, selectedProductId, onSelectProduct }: CloudProductRailProps) {
  return (
    <aside className="cloud-product-rail" aria-label="产品选择">
      <div className="cloud-panel-title">
        <strong>产品</strong>
        <span>{products.length} 个产品</span>
      </div>
      {products.map(product => {
        const phoneCount = product.ipGroups.reduce((sum, ipGroup) => sum + ipGroup.phoneCount, 0);
        const active = selectedProductId === product.id;
        return (
          <button
            className={`cloud-product-card ${active ? 'active' : ''}`}
            type="button"
            onClick={() => onSelectProduct(product.id)}
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
  );
}

type CloudSeatToolbarProps = {
  selectedProduct?: CloudProduct;
  selectedPhoneTitle: string;
  selectedSlot?: SelectedCloudPhoneSlot;
  totals: CloudPhoneTotals;
};

export function CloudSeatToolbar({ selectedProduct, selectedPhoneTitle, selectedSlot, totals }: CloudSeatToolbarProps) {
  return (
    <div className="cloud-seat-toolbar">
      <div>
        <span>{selectedProduct?.code}</span>
        <h2>{selectedProduct?.name} IP 分组视图</h2>
        <p className="cloud-selection-inline">
          {selectedSlot
            ? `${selectedPhoneTitle} · ${selectedSlot.groupName || selectedSlot.ipGroup.name} · ${stateLabels[selectedSlot.state]}`
            : '点击任意云手机后，会弹出 GeeLark 分组、国家、serialNo、运行状态和 tags。'}
        </p>
      </div>
      <div className="cloud-seat-summary">
        <span><b>{totals.ipGroups}</b> IP 分组</span>
        <span><b>{formatNumber(totals.active)}</b> 可用手机</span>
        <span><b>{formatNumber(totals.warnings)}</b> 待检查</span>
      </div>
    </div>
  );
}

type CloudCountryStackProps = {
  countrySections: CountrySection[];
  selectedProductCode?: string;
  selectedSlotId: string;
  onSelectSlot: (slotId: string) => void;
};

export function CloudCountryStack({ countrySections, selectedProductCode, selectedSlotId, onSelectSlot }: CloudCountryStackProps) {
  if (!countrySections.length) {
    return (
      <div className="cloud-empty-state">
        当前产品暂未匹配到 GeeLark 分组。请确认分组名里包含产品 code 和国家 code，例如 GE-DB 或 DB-GE。
      </div>
    );
  }

  return (
    <div className="cloud-country-stack">
      {countrySections.map(section => (
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
              const displayName = compactIpGroupName(ipGroup.name, ipGroup.code, selectedProductCode || '');
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
                        onClick={() => onSelectSlot(selectedSlotId === slot.id ? '' : slot.id)}
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
      ))}
    </div>
  );
}

type CloudPhoneDetailLayerProps = {
  selectedPhoneTitle: string;
  selectedSlot?: SelectedCloudPhoneSlot;
  onClose: () => void;
};

export function CloudPhoneDetailLayer({ selectedPhoneTitle, selectedSlot, onClose }: CloudPhoneDetailLayerProps) {
  if (!selectedSlot) return null;

  return (
    <div
      className="cloud-phone-detail-layer"
      role="dialog"
      aria-modal="false"
      aria-label="云手机详情"
      onClick={onClose}
    >
      <div className="cloud-phone-detail-card" onClick={event => event.stopPropagation()}>
        <button className="cloud-detail-close" type="button" onClick={onClose} aria-label="关闭详情">
          ×
        </button>
        <span className={`cloud-detail-state ${selectedSlot.state}`}>{stateLabels[selectedSlot.state]}</span>
        <h3>{selectedPhoneTitle}</h3>
        <p>{selectedSlot.groupName || selectedSlot.ipGroup.name}</p>
        <dl>
          <div><dt>国家/地区</dt><dd>{selectedSlot.countryName || selectedSlot.ipGroup.countryName}</dd></div>
          <div><dt>分组</dt><dd>{selectedSlot.groupName || selectedSlot.ipGroup.name}</dd></div>
          <div><dt>Serial Name</dt><dd>{selectedSlot.serialName || '—'}</dd></div>
          <div><dt>Serial No</dt><dd>{selectedSlot.serialNo || selectedSlot.label}</dd></div>
          <div><dt>RPA</dt><dd>{selectedSlot.rpaStatus ?? '—'}</dd></div>
          <div><dt>时区</dt><dd>{selectedSlot.timeZone || '—'}</dd></div>
          <div><dt>设备</dt><dd>{selectedSlot.deviceModel || '—'}</dd></div>
          <div><dt>Tags</dt><dd>{selectedSlot.tags?.join(' · ') || '—'}</dd></div>
        </dl>
      </div>
    </div>
  );
}
