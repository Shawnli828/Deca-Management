'use client';

import { useState } from 'react';
import type { FeishuCardData } from '@/lib/types';
import {
  cardMetric,
  cardRate,
  postCoverage,
  productInitials,
  productKey,
  type FeishuProductCardData
} from './FeishuReportShared';
import { FeishuCountryAvgTrendChart } from './FeishuTrendCharts';

export function FeishuProductPreviewPanel({
  products,
  countryAvgTrend
}: {
  products: NonNullable<FeishuCardData['products']>;
  countryAvgTrend: NonNullable<FeishuCardData['countryAvgTrend']>;
}) {
  const firstCode = productKey(products[0]);
  const [selectedCode, setSelectedCode] = useState(firstCode);
  const activeCode = productKey(products.find(product => productKey(product) === selectedCode)) || firstCode;
  const selectedProduct = products.find(product => productKey(product) === activeCode) || products[0];
  const selectedTrend = selectedProduct ? countryAvgTrend[productKey(selectedProduct)] || [] : [];

  return (
    <aside className="feishu-native-product-panel">
      <div className="feishu-native-panel-head">
        <div>
          <div className="feishu-native-section-title">产品视图</div>
          <p>单产品业务日数据 · 国家 RF 均播</p>
        </div>
        <span>中台产品预览</span>
      </div>
      {products.length && selectedProduct ? (
        <>
          <ProductSwitcher products={products} activeCode={activeCode} onSelect={setSelectedCode} />
          <ProductKpis product={selectedProduct} />
          <ProductAnomalyTables product={selectedProduct} />
          <CountryAvgTable countries={selectedProduct.countries || []} />
          <FeishuCountryAvgTrendChart
            title={`${selectedProduct.name || selectedProduct.code || 'Product'} · 国家 RF 均播趋势`}
            countries={selectedTrend}
          />
        </>
      ) : (
        <p className="feishu-native-empty">暂无产品数据。</p>
      )}
    </aside>
  );
}

function ProductSwitcher({
  products,
  activeCode,
  onSelect
}: {
  products: NonNullable<FeishuCardData['products']>;
  activeCode: string;
  onSelect: (code: string) => void;
}) {
  return (
    <div className="feishu-product-switcher" role="tablist" aria-label="选择产品">
      {products.map(product => {
        const key = productKey(product);
        const active = key === activeCode;
        return (
          <button
            type="button"
            role="tab"
            aria-selected={active}
            className={active ? 'is-active' : undefined}
            key={key || product.name || product.code}
            onClick={() => onSelect(key)}
          >
            <span className="feishu-product-logo-mark" aria-hidden="true">{productInitials(product)}</span>
            <span>{product.name || product.code || 'Product'}</span>
          </button>
        );
      })}
    </div>
  );
}

function ProductKpis({ product }: { product: FeishuProductCardData }) {
  const items = [
    { label: 'View', value: cardMetric(product.totalPlays), tone: 'is-primary', span: 2 },
    { label: 'RF Total View', value: cardMetric(product.rfPlays), tone: '', span: 2 },
    { label: 'Clone Total View', value: cardMetric(product.clonePlays), tone: '', span: 2 },
    { label: 'Unique Onboarding', value: product.onboarding === null ? '—' : cardMetric(product.onboarding), tone: 'is-green', span: 3 },
    { label: '转化', value: cardRate(product.downloadRate), tone: 'is-amber', span: 3 },
    { label: 'Post', value: postCoverage(product), tone: '', span: 3 },
    {
      label: '未发 / 0播放',
      value: `${cardMetric(product.unsent)} / ${cardMetric(product.zeroPlay)}`,
      tone: (Number(product.unsent || 0) || Number(product.zeroPlay || 0)) ? 'is-red' : '',
      span: 3,
    },
  ];

  return (
    <div className="feishu-product-kpi-grid">
      {items.map(item => (
        <article
          className={`${item.tone || ''} span-${item.span}`.trim()}
          key={item.label}
        >
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </div>
  );
}

function findAnomalyGroup(product: FeishuProductCardData, marker: string) {
  return (product.anomalyGroups || []).find(group => String(group.title || '').includes(marker));
}

function ProductAnomalyTables({ product }: { product: FeishuProductCardData }) {
  const unsentGroup = findAnomalyGroup(product, '未发送');
  const zeroPlayGroup = findAnomalyGroup(product, '0播');

  return (
    <div className="feishu-anomaly-detail-section">
      <div className="feishu-anomaly-table-grid">
        <ProductAnomalyTable
          title="未发账号"
          count={Number(product.unsent || 0)}
          accounts={unsentGroup?.accounts || []}
          more={unsentGroup?.more || null}
          emptyText="暂无未发账号。"
          tone="is-red"
        />
        <ProductAnomalyTable
          title="0播放警告"
          count={Number(product.zeroPlay || 0)}
          accounts={zeroPlayGroup?.accounts || []}
          more={zeroPlayGroup?.more || null}
          emptyText="暂无 0 播账号。"
          tone="is-amber"
        />
      </div>
    </div>
  );
}

function ProductAnomalyTable({
  title,
  count,
  accounts,
  more,
  emptyText,
  tone
}: {
  title: string;
  count: number;
  accounts: NonNullable<FeishuProductCardData['anomalyGroups']>[number]['accounts'];
  more?: string | null;
  emptyText: string;
  tone: 'is-red' | 'is-amber';
}) {
  const rows = accounts || [];

  return (
    <div className="feishu-anomaly-table">
      <div className={`feishu-anomaly-table-title ${tone}`}>
        <strong>{title}</strong>
        <span>{cardMetric(count)}</span>
      </div>
      <div className="feishu-anomaly-table-body">
        <div className="feishu-anomaly-row is-head">
          <span>TikTok 账号</span>
          <span>Automation / RF</span>
        </div>
        {rows.length ? rows.map((account, index) => (
          <div
            className="feishu-anomaly-row"
            key={`${title}-${account.handle || 'account'}-${account.batch || 'batch'}-${index}`}
          >
            <span>{account.flag || '🌐'} {account.handle || '—'}</span>
            <strong>{account.batch || '—'}</strong>
          </div>
        )) : (
          <div className="feishu-anomaly-row is-empty">
            <span>{emptyText}</span>
            <strong>—</strong>
          </div>
        )}
        {more ? <div className="feishu-anomaly-more">{more}</div> : null}
      </div>
    </div>
  );
}

function CountryAvgTable({
  countries
}: {
  countries: NonNullable<NonNullable<FeishuCardData['products']>[number]['countries']>;
}) {
  return (
    <div className="feishu-country-avg-section">
      <div className="feishu-native-section-title">国家业务日 RF 均播</div>
      <div className="feishu-country-avg-table">
        <div className="feishu-country-avg-row is-head">
          <span>国家</span>
          <span>RF Avg View</span>
          <span>Post</span>
        </div>
        {countries.length ? countries.map(country => (
          <div className="feishu-country-avg-row" key={`${country.name || 'country'}-${country.flag || ''}`}>
            <span>{country.flag || '🌐'} {country.name || 'Country'}</span>
            <strong>{country.rfAvg === null ? '—' : cardMetric(country.rfAvg)}</strong>
            <strong>{cardMetric(country.posts)}</strong>
          </div>
        )) : (
          <p className="feishu-native-empty">暂无国家均播数据。</p>
        )}
      </div>
    </div>
  );
}

