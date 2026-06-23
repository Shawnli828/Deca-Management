'use client';

import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { formatFeishuMetric } from '@/lib/feishuReportHelpers';
import type { FeishuGrowthSyncResult, FeishuSourceSyncResult } from '@/hooks/useFeishuReport';
import type {
  DailyFeishuProductSummary,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  FeishuCardData,
  FeishuSendMode
} from '@/lib/types';

type FeishuProductCardData = NonNullable<FeishuCardData['products']>[number];

export function FeishuReportLayout({
  payload,
  loading,
  reportDate,
  products,
  sendMode
}: {
  payload: DailyFeishuPreviewPayload | null;
  loading: boolean;
  reportDate: string;
  products: DailyFeishuProductSummary[];
  sendMode: FeishuSendMode;
}) {
  const showCardPreview = Boolean(payload?.card_data);
  return (
    <>
      {showCardPreview ? <FeishuNativeCardPreview data={payload?.card_data || null} loading={loading} /> : null}
      <div className="feishu-report-layout">
        <section className="feishu-message-card">
          <div className="feishu-card-head">
            <div>
              <h2>{sendMode === 'image' ? '图片看板数据预览' : sendMode === 'template' ? '模板卡片数据预览' : '文本兜底预览'}</h2>
              <p>
                业务日 {payload?.report?.report_date || reportDate} · 内容窗口{' '}
                {payload?.report?.business_window_local?.start || '—'} → {payload?.report?.business_window_local?.end || '—'}
              </p>
            </div>
          </div>
          <pre className="feishu-message-preview">{payload?.message || (loading ? '正在生成...' : '暂无预览')}</pre>
          {sendMode === 'template' && payload?.template_preview ? (
            <details className="feishu-template-preview">
              <summary>模板变量预览</summary>
              <pre>{JSON.stringify(payload.template_preview, null, 2)}</pre>
            </details>
          ) : null}
        </section>

        <aside className="feishu-product-card">
          <div className="feishu-card-head">
            <div>
              <h2>产品拆分</h2>
              <p>用于检查发送前每个产品的数据是否合理。</p>
            </div>
          </div>
          <div className="feishu-product-list">
            {products.length ? products.map(product => (
              <article key={String(product.product_code || product.product_name)}>
                <div>
                  <strong>{String(product.product_name || product.product_code || 'Product')}</strong>
                  <span>{String(product.product_code || '')}</span>
                </div>
                <small>播放 {formatFeishuMetric(product.total_views)} · Onboarding {formatFeishuMetric(product.downloads)}</small>
              </article>
            )) : (
              <p className="feishu-empty">暂无产品数据。</p>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

function cardMetric(value: unknown) {
  return formatFeishuMetric(value);
}

function cardRate(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${formatFeishuMetric(value)}%`;
  return `${numeric.toFixed(2)}%`;
}

function postCoverage(product: { rfPublished?: number; rfExpected?: number }) {
  return `${cardMetric(product.rfPublished)}/${cardMetric(product.rfExpected)}`;
}

function compactAxisMetric(value: number) {
  if (!Number.isFinite(value)) return '0';
  const abs = Math.abs(value);
  if (abs >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (abs >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(Math.round(value));
}

function paddedRange(values: number[]) {
  const finite = values.filter(value => Number.isFinite(value));
  if (!finite.length) return { min: 0, max: 1 };
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) {
    const pad = Math.max(1, Math.abs(max) * 0.1);
    return { min: Math.max(0, min - pad), max: max + pad };
  }
  const pad = (max - min) * 0.12;
  return { min: Math.max(0, min - pad), max: max + pad };
}

function ceilToStep(value: number, step: number) {
  return Math.ceil(value / step) * step;
}

function countryTrendAxis(values: number[]) {
  const finite = values.filter(value => Number.isFinite(value));
  if (!finite.length) {
    return {
      min: 0,
      max: 1000,
      ticks: [0, 200, 400, 600, 800, 1000],
    };
  }
  const rawMax = Math.max(...finite, 1);
  const max = Math.max(1000, ceilToStep(rawMax * 1.08, 200));
  const ticks: number[] = [];
  for (let value = 0; value <= max; value += 200) {
    ticks.push(value);
  }
  return {
    min: 0,
    max,
    ticks,
  };
}

function allLabelIndexes(count: number) {
  return Array.from({ length: count }, (_, index) => index);
}

function xAxisLabelAnchor(index: number, count: number) {
  if (index === 0) return 'start';
  if (index === count - 1) return 'end';
  return 'middle';
}

function OverviewNativePreview({ data }: { data: FeishuCardData }) {
  const overviewTrend = overviewTrendGroup(data);

  return (
    <div className="feishu-native-dashboard">
      <section className="feishu-native-overview-panel">
        <div className="feishu-native-panel-head">
          <div>
            <div className="feishu-native-section-title">总览 · 甲方产品</div>
            <p>业务日 {data.bizDate || '—'} · 内容窗口 {data.window || '—'}</p>
          </div>
          <span>Webhook 总览卡片</span>
        </div>
        <FeishuOverviewKpis global={data.global || {}} />
        <FeishuTrendPanel groups={[overviewTrend]} />
      </section>
      <FeishuProductPreviewPanel products={data.products || []} countryAvgTrend={data.countryAvgTrend || {}} />
    </div>
  );
}

function overviewTrendGroup(data: FeishuCardData) {
  const groups = data.trendGroups || [];
  return (
    groups.find(group => String(group.key || '').toLowerCase() === 'overview')
    || groups.find(group => String(group.label || '') === '总览')
    || { key: 'overview', label: '总览', trend: data.trend || [] }
  );
}

function FeishuOverviewKpis({
  global
}: {
  global: NonNullable<FeishuCardData['global']>;
}) {
  const items = [
    ['总播放', cardMetric(global.totalPlays), 'is-primary'],
    ['RF Total View', cardMetric(global.rfPlays), ''],
    ['Clone Total View', cardMetric(global.clonePlays), ''],
    ['Onboarding Unique', global.onboarding === null ? '—' : cardMetric(global.onboarding), 'is-green'],
    ['转化', cardRate(global.downloadRate), 'is-amber'],
    ['Post', postCoverage(global), '']
  ];

  return (
    <div className="feishu-native-kpi-grid">
      {items.map(([label, value, tone]) => (
        <article className={tone ? String(tone) : undefined} key={String(label)}>
          <span>{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </div>
  );
}

function FeishuProductPreviewPanel({
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

function productKey(product?: FeishuProductCardData) {
  return String(product?.code || product?.name || '').trim().toUpperCase();
}

function productInitials(product?: FeishuProductCardData) {
  const code = String(product?.code || '').trim().toUpperCase();
  if (code) return code.slice(0, 3);
  const label = String(product?.name || product?.code || 'P').trim();
  const parts = label.split(/[\s_-]+/).filter(Boolean);
  if (parts.length > 1) return parts.map(part => part[0]).join('').slice(0, 2).toUpperCase();
  return label.slice(0, 2).toUpperCase();
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

const countryTrendColors = ['#2f8af5', '#0f766e', '#a16207', '#7c3aed', '#dc2626', '#475569', '#0891b2'];

function svgSmoothPath(points: Array<{ x: number; y: number }>) {
  if (!points.length) return '';
  if (points.length === 1) return `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  return points.slice(1).reduce((path, point, index) => {
    const previous = points[index];
    const midX = (previous.x + point.x) / 2;
    return `${path} C${midX.toFixed(1)} ${previous.y.toFixed(1)} ${midX.toFixed(1)} ${point.y.toFixed(1)} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
  }, `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`);
}

function FeishuCountryAvgTrendChart({
  title,
  countries
}: {
  title: string;
  countries: NonNullable<FeishuCardData['countryAvgTrend']>[string];
}) {
  const baseChart = useMemo(() => {
    const labelMap = new Map<string, { date: string; label: string }>();
    const seriesSource = (countries || []).map((country, index) => {
      const rows = (country.rows || [])
        .map(row => ({
          date: String(row.date || '').slice(0, 10),
          label: row.label || String(row.date || '').slice(5, 10),
          rfAvg: row.rfAvg === null || row.rfAvg === undefined ? null : Number(row.rfAvg),
          posts: Number(row.posts || 0),
        }))
        .filter(row => row.date && row.rfAvg !== null && Number.isFinite(row.rfAvg));
      rows.forEach(row => labelMap.set(row.date, { date: row.date, label: row.label }));
      const countryName = country.countryName || country.countryCode || 'Country';
      return {
        id: `${country.countryCode || countryName}-${index}`,
        countryName,
        flag: country.flag || '🌐',
        color: countryTrendColors[index % countryTrendColors.length],
        rows,
      };
    }).filter(country => country.rows.length);

    const labels = Array.from(labelMap.values()).sort((a, b) => a.date.localeCompare(b.date));
    return { labels, seriesSource };
  }, [countries]);

  const countrySelectionKey = baseChart.seriesSource.map(series => series.id).join('|');
  const [selectedCountryIds, setSelectedCountryIds] = useState<string[]>([]);

  useEffect(() => {
    setSelectedCountryIds(baseChart.seriesSource.map(series => series.id));
  }, [countrySelectionKey, baseChart.seriesSource]);

  const selectedIdSet = useMemo(() => {
    const activeIds = selectedCountryIds.length
      ? selectedCountryIds
      : baseChart.seriesSource.map(series => series.id);
    return new Set(activeIds);
  }, [selectedCountryIds, baseChart.seriesSource]);

  const chart = useMemo(() => {
    const labels = baseChart.labels;
    const visibleSource = baseChart.seriesSource.filter(country => selectedIdSet.has(country.id));
    const seriesSource = visibleSource.length ? visibleSource : baseChart.seriesSource;
    const values = seriesSource.flatMap(country => country.rows.map(row => Number(row.rfAvg || 0)));
    const width = 1040;
    const pad = { top: 46, right: 36, bottom: 42, left: 62 };
    const axis = countryTrendAxis(values);
    const tickIntervals = Math.max(1, (axis.max - axis.min) / 200);
    const height = pad.top + pad.bottom + Math.max(360, tickIntervals * 38);
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const xFor = (index: number) => pad.left + (labels.length <= 1 ? plotWidth / 2 : (plotWidth / (labels.length - 1)) * index);
    const yFor = (value: number) => {
      const clamped = Math.min(axis.max, Math.max(axis.min, value));
      const ratio = (clamped - axis.min) / Math.max(1, axis.max - axis.min);
      return pad.top + plotHeight - ratio * plotHeight;
    };
    const labelIndexes = allLabelIndexes(labels.length);
    const series = seriesSource.map(country => {
      const rowsByDate = new Map(country.rows.map(row => [row.date, row]));
      const points = labels
        .map((label, labelIndex) => {
          const row = rowsByDate.get(label.date);
          if (!row || row.rfAvg === null) return null;
          return {
            x: xFor(labelIndex),
            y: yFor(row.rfAvg),
            value: row.rfAvg,
            date: label.date,
          };
        })
        .filter(Boolean) as Array<{ x: number; y: number; value: number; date: string }>;
      return {
        ...country,
        points,
        path: svgSmoothPath(points),
      };
    });
    const grid = axis.ticks.map(value => ({
      y: yFor(value),
      value,
    }));
    return { labels, width, height, pad, series, grid, labelIndexes };
  }, [baseChart, selectedIdSet]);

  const toggleCountry = (countryId: string) => {
    setSelectedCountryIds(current => {
      const activeIds = current.length ? current : baseChart.seriesSource.map(series => series.id);
      const isActive = activeIds.includes(countryId);
      if (isActive && activeIds.length <= 1) return activeIds;
      return isActive
        ? activeIds.filter(id => id !== countryId)
        : [...activeIds, countryId];
    });
  };

  if (!baseChart.seriesSource.length || !baseChart.labels.length) {
    return (
      <div className="feishu-country-trend is-empty">
        <div className="feishu-native-section-title">{title}</div>
        <p>暂无国家均播趋势。</p>
      </div>
    );
  }

  return (
    <div className="feishu-country-trend">
      <div className="feishu-country-trend-head">
        <div className="feishu-native-section-title">{title}</div>
        <div className="feishu-country-legend">
          {baseChart.seriesSource.map(series => {
            const active = selectedIdSet.has(series.id);
            return (
              <button
                type="button"
                key={series.id}
                className={active ? 'is-active' : 'is-muted'}
                style={{ '--series-color': series.color } as CSSProperties}
                aria-pressed={active}
                onClick={() => toggleCountry(series.id)}
              >
                {series.flag} {series.countryName}
              </button>
            );
          })}
        </div>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        width={chart.width}
        height={chart.height}
        role="img"
        aria-label={title}
      >
        {chart.grid.map(line => (
          <g key={`country-grid-${line.y}`}>
            <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={line.y} y2={line.y} />
            <text className="is-y-label" x={chart.pad.left - 8} y={line.y + 3} textAnchor="end">
              {compactAxisMetric(line.value)}
            </text>
          </g>
        ))}
        {chart.series.map(series => (
          <g key={`country-series-${series.countryName}`}>
            <path d={series.path} style={{ stroke: series.color }} />
            {series.points.map(point => (
              <g key={`${series.countryName}-${point.date}`}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r="2.2"
                  style={{ fill: series.color }}
                />
                <text
                  className="is-point-label"
                  x={point.x}
                  y={Math.max(chart.pad.top - 10, point.y - 8)}
                  textAnchor="middle"
                  style={{ fill: series.color }}
                >
                  {compactAxisMetric(point.value)}
                </text>
              </g>
            ))}
          </g>
        ))}
        {chart.labelIndexes.map(index => (
          <text
            className="is-x-label"
            x={chart.pad.left + (chart.labels.length <= 1 ? (chart.width - chart.pad.left - chart.pad.right) / 2 : ((chart.width - chart.pad.left - chart.pad.right) / (chart.labels.length - 1)) * index)}
            y={chart.height - 7}
            textAnchor={xAxisLabelAnchor(index, chart.labels.length)}
            key={`country-label-${chart.labels[index].date}`}
          >
            {chart.labels[index].label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function FeishuTrendPanel({
  groups
}: {
  groups: NonNullable<FeishuCardData['trendGroups']>;
}) {
  const visibleGroups = groups.slice(0, 4);

  return (
    <div className="feishu-native-trend">
      <div className="feishu-native-trend-head">
        <div className="feishu-native-section-title">View / Download 趋势</div>
        <div className="feishu-native-legend">
          <span className="is-view">View</span>
          <span className="is-download">Download</span>
        </div>
      </div>
      {visibleGroups.length ? (
        <div className={`feishu-native-trend-grid${visibleGroups.length === 1 ? ' is-single' : ''}`}>
          {visibleGroups.map(group => (
            <FeishuMiniTrendChart
              key={group.key || group.label}
              title={(group.label || group.key) === '总览' ? '全部汇总' : (group.label || group.key || '趋势')}
              trend={group.trend || []}
              wide={visibleGroups.length === 1}
            />
          ))}
        </div>
      ) : (
        <p>暂无趋势数据。</p>
      )}
    </div>
  );
}

function FeishuMiniTrendChart({
  title,
  trend,
  wide = false
}: {
  title: string;
  trend: NonNullable<FeishuCardData['trend']>;
  wide?: boolean;
}) {
  const chart = useMemo(() => {
    const rows = trend.map(row => ({
      label: row.label || row.date || '',
      view: Number(row.view || 0),
      download: Number(row.download || 0)
    }));
    const width = wide ? 920 : 320;
    const height = wide ? 300 : 170;
    const pad = wide
      ? { top: 16, right: 58, bottom: 34, left: 58 }
      : { top: 12, right: 36, bottom: 26, left: 42 };
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const viewRange = paddedRange(rows.map(row => row.view));
    const downloadRange = paddedRange(rows.map(row => row.download));
    const xFor = (index: number) => pad.left + (rows.length <= 1 ? plotWidth / 2 : (plotWidth / (rows.length - 1)) * index);
    const yFor = (value: number, range: { min: number; max: number }) => {
      const ratio = (value - range.min) / Math.max(1, range.max - range.min);
      return pad.top + plotHeight - ratio * plotHeight;
    };
    const viewPoints = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.view, viewRange), value: row.view }));
    const downloadPoints = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.download, downloadRange), value: row.download }));
    const labelYFor = (pointY: number, offset: number) => Math.min(
      height - pad.bottom - 4,
      Math.max(pad.top + 8, pointY + offset)
    );
    const pathFor = (points: Array<{ x: number; y: number }>) => {
      if (!points.length) return '';
      if (points.length === 1) return `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
      return points.slice(1).reduce((path, point, index) => {
        const previous = points[index];
        const midX = (previous.x + point.x) / 2;
        return `${path} C${midX.toFixed(1)} ${previous.y.toFixed(1)} ${midX.toFixed(1)} ${point.y.toFixed(1)} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
      }, `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`);
    };
    const grid = Array.from({ length: 4 }, (_, index) => {
      const ratio = index / 3;
      return {
        y: pad.top + ratio * plotHeight,
        view: viewRange.max - ratio * (viewRange.max - viewRange.min),
        download: downloadRange.max - ratio * (downloadRange.max - downloadRange.min),
      };
    });
    const labelIndexes = allLabelIndexes(rows.length);
    return {
      rows,
      width,
      height,
      pad,
      viewPoints,
      downloadPoints,
      labelYFor,
      viewPath: pathFor(viewPoints),
      downloadPath: pathFor(downloadPoints),
      grid,
      labelIndexes,
    };
  }, [trend, wide]);

  if (!chart.rows.length) {
    return (
      <div className={`feishu-native-mini-chart is-empty${wide ? ' is-wide' : ''}`}>
        <div className="feishu-native-mini-chart-head">
          <strong>{title}</strong>
        </div>
        <p>暂无趋势数据。</p>
      </div>
    );
  }

  return (
    <div className={`feishu-native-mini-chart${wide ? ' is-wide' : ''}`}>
      <div className="feishu-native-mini-chart-head">
        <strong>{title}</strong>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        width={chart.width}
        height={chart.height}
        role="img"
        aria-label={`${title} View and Download trend`}
      >
          {chart.grid.map(line => (
            <g key={`grid-${line.y}`}>
              <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={line.y} y2={line.y} />
              <text className="is-y-label" x={chart.pad.left - 8} y={line.y + 3} textAnchor="end">
                {compactAxisMetric(line.view)}
              </text>
              <text className="is-y-label" x={chart.width - chart.pad.right + 8} y={line.y + 3} textAnchor="start">
                {compactAxisMetric(line.download)}
              </text>
            </g>
          ))}
          <path className="is-view-line" d={chart.viewPath} />
          <path className="is-download-line" d={chart.downloadPath} />
          {chart.viewPoints.map((point, index) => (
            <circle className="is-view-point" cx={point.x} cy={point.y} r="2.2" key={`view-${index}-${chart.rows[index].label}`} />
          ))}
          {chart.downloadPoints.map((point, index) => (
            <circle className="is-download-point" cx={point.x} cy={point.y} r="2.2" key={`download-${index}-${chart.rows[index].label}`} />
          ))}
          {chart.viewPoints.map((point, index) => (
            <text
              className="is-point-label is-view-label"
              x={point.x}
              y={chart.labelYFor(point.y, -9)}
              textAnchor="middle"
              key={`view-label-${index}-${chart.rows[index].label}`}
            >
              {compactAxisMetric(point.value)}
            </text>
          ))}
          {chart.downloadPoints.map((point, index) => (
            <text
              className="is-point-label is-download-label"
              x={point.x}
              y={chart.labelYFor(point.y, 14)}
              textAnchor="middle"
              key={`download-label-${index}-${chart.rows[index].label}`}
            >
              {compactAxisMetric(point.value)}
            </text>
          ))}
          {chart.labelIndexes.map(index => (
            <text
              className="is-x-label"
              x={chart.viewPoints[index].x}
              y={chart.height - 6}
              textAnchor={xAxisLabelAnchor(index, chart.rows.length)}
              key={`label-${index}-${chart.rows[index].label}`}
            >
              {chart.rows[index].label}
            </text>
          ))}
        </svg>
    </div>
  );
}

function FeishuNativeCardPreview({ data, loading }: { data: FeishuCardData | null; loading: boolean }) {
  if (!data) {
    return (
      <section className="feishu-native-preview">
        <div className="feishu-native-empty">{loading ? '正在生成飞书卡片预览...' : '暂无飞书卡片预览'}</div>
      </section>
    );
  }

  return (
    <section className="feishu-native-preview">
      <OverviewNativePreview data={data} />
    </section>
  );
}

export function FeishuStatusMessages({
  error,
  sendResult,
  growthSyncResult,
  sourceSyncResult
}: {
  error: string;
  sendResult: DailyFeishuSendResult | null;
  growthSyncResult: FeishuGrowthSyncResult | null;
  sourceSyncResult: FeishuSourceSyncResult | null;
}) {
  return (
    <>
      {error ? <div className="growth-error">{error}</div> : null}
      {sourceSyncResult ? (
        <div className={sourceSyncResult.ok ? 'feishu-success' : 'feishu-sync-partial'}>
          RF / Museon 同步{sourceSyncResult.ok ? '完成' : '未完成'}
          {sourceSyncResult.reelfarm ? `：RF ${sourceSyncResult.reelfarm.records_count || 0} 条` : ''}
          {sourceSyncResult.museon ? ` · Museon ${sourceSyncResult.museon.records_count || 0} 条` : ''}
          {sourceSyncResult.error ? ` · ${sourceSyncResult.error}` : ''}
        </div>
      ) : null}
      {growthSyncResult?.products.length ? (
        <div className={growthSyncResult.ok ? 'feishu-success' : 'feishu-sync-partial'}>
          Mixpanel 缓存同步完成：{growthSyncResult.products.map(item => `${item.productCode} ${item.count} 条快照`).join(' · ')}
          {growthSyncResult.errors.length ? ` · 失败 ${growthSyncResult.errors.length} 个产品` : ''}
        </div>
      ) : null}
      {sendResult?.ok ? (
        <div className="feishu-success">
          已发送到飞书：{sendResult.sent_at || '刚刚'}
          {sendResult.mode ? ` · ${
            sendResult.mode === 'image'
              ? 'SVG 图片看板'
              : sendResult.mode === 'template'
              ? '模板卡片模式'
              : sendResult.mode === 'card'
                ? 'Webhook 卡片模式'
                : sendResult.fallback_reason
                  ? 'Webhook 卡片失败转文本'
                  : 'Webhook 卡片优先模式'
          }` : ''}
        </div>
      ) : null}
    </>
  );
}
