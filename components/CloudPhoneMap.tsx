'use client';

import type { Product } from '@/lib/types';
import { formatNumber } from '@/lib/utils';
import { useCloudPhoneMap } from '@/hooks/useCloudPhoneMap';
import { compactIpGroupName, stateLabels } from './CloudPhoneMapHelpers';

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
  const {
    cloudProducts,
    countrySections,
    geeLarkError,
    geeLarkLoading,
    liveLabel,
    selectedPhoneTitle,
    selectedProduct,
    selectedSlot,
    selectedSlotId,
    setSelectedProductId,
    setSelectedSlotId,
    totals
  } = useCloudPhoneMap(products);

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
                              onClick={() => setSelectedSlotId(selectedSlotId === slot.id ? '' : slot.id)}
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
      </div>

      {selectedSlot ? (
        <div
          className="cloud-phone-detail-layer"
          role="dialog"
          aria-modal="false"
          aria-label="云手机详情"
          onClick={() => setSelectedSlotId('')}
        >
          <div className="cloud-phone-detail-card" onClick={event => event.stopPropagation()}>
            <button className="cloud-detail-close" type="button" onClick={() => setSelectedSlotId('')} aria-label="关闭详情">
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
      ) : null}
    </section>
  );
}
