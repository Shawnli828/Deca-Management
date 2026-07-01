'use client';

import { useEffect, useMemo, useState } from 'react';
import { WorkspaceHeader } from '@/components/dashboard/WorkspaceHeader';
import { businessIsoDate } from '@/hooks/useBusinessMaterialReport';
import { api, getErrorMessage } from '@/lib/api';
import type { ABTestDailyRow, ABTestRecord, ABTestMetricTotals, Product } from '@/lib/types';
import { countryFlag, getCountryReelFarmCode, getProductReelFarmCode, normalizeProductFolder } from '@/lib/utils';
import { metric, percent } from '@/lib/businessReportFormatters';

type ABTestPageProps = {
  active: boolean;
  products: Product[];
};

type ABTestForm = {
  name: string;
  productId: string;
  countryId: string;
  startDate: string;
  durationDays: number;
  variable: string;
  hypothesis: string;
  note: string;
};

const STATUS_LABELS: Record<string, string> = {
  draft: '未开始',
  running: '进行中',
  ready: '待复盘',
  completed: '已完成'
};

const CONCLUSION_OPTIONS = [
  { value: 'undecided', label: '未判断' },
  { value: 'valid', label: '有效' },
  { value: 'invalid', label: '无效' },
  { value: 'inconclusive', label: '不确定' }
];

const CONCLUSION_LABELS = Object.fromEntries(CONCLUSION_OPTIONS.map(option => [option.value, option.label]));
const STATUS_SORT: Record<string, number> = { running: 0, ready: 1, draft: 2, completed: 3 };

function numberMetric(value: unknown) {
  return metric(value);
}

function signedPercent(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  const number = Number(value);
  return `${number > 0 ? '+' : ''}${number.toFixed(1)}%`;
}

function signedNumber(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  const number = Number(value);
  return `${number > 0 ? '+' : ''}${metric(number)}`;
}

function compactDate(value?: string) {
  return String(value || '').slice(5, 10) || '—';
}

function productOptions(products: Product[]) {
  return products.filter(product => normalizeProductFolder(product) !== '乙方');
}

function initials(value?: string) {
  const text = String(value || '').trim();
  if (!text) return 'APP';
  return text.split(/\s+/).map(part => part[0]).join('').slice(0, 3).toUpperCase();
}

function abTestProductCode(test: ABTestRecord) {
  return String(test.product_code || '').trim().toUpperCase();
}

function abTestCountryCode(test: ABTestRecord) {
  return String(test.country_code || '').trim().toUpperCase();
}

function compareTests(left: ABTestRecord, right: ABTestRecord) {
  const statusDelta = (STATUS_SORT[left.status || 'draft'] ?? 9) - (STATUS_SORT[right.status || 'draft'] ?? 9);
  if (statusDelta) return statusDelta;
  return String(right.start_date || '').localeCompare(String(left.start_date || ''));
}

function dailyOnboardingText(row: ABTestDailyRow) {
  if (row.onboarding_scope === 'unavailable' || row.onboarding_filter_supported === false) return '—';
  return numberMetric(row.onboarding_unique ?? 0);
}

function dailyConversionText(row: ABTestDailyRow) {
  if (row.conversion_rate === null || row.conversion_rate === undefined) return '—';
  return percent(row.conversion_rate);
}

function emptyForm(products: Product[]): ABTestForm {
  const candidates = productOptions(products);
  const firstProduct = candidates[0] || products[0];
  return {
    name: '',
    productId: firstProduct?.id || '',
    countryId: firstProduct?.countries?.[0]?.id || '',
    startDate: businessIsoDate(),
    durationDays: 7,
    variable: '',
    hypothesis: '',
    note: ''
  };
}

function rangeText(test?: ABTestRecord, kind: 'test' | 'control' = 'test') {
  const range = test?.periods?.[kind];
  if (!range) return '—';
  return `${range.date_from} → ${range.date_to}`;
}

function statusClass(status?: string) {
  if (status === 'completed') return 'completed';
  if (status === 'ready') return 'ready';
  if (status === 'running') return 'running';
  return 'draft';
}

function metricCard(label: string, control: unknown, test: unknown, delta: unknown, percentDelta?: number | null) {
  return { label, control, test, delta, percentDelta };
}

function onboardingText(totals?: ABTestMetricTotals) {
  if (totals?.onboarding_scope === 'unavailable') return '无国家字段';
  return numberMetric(totals?.onboarding_unique);
}

export function ABTestPage({ active, products }: ABTestPageProps) {
  const visibleProducts = useMemo(() => productOptions(products), [products]);
  const [tests, setTests] = useState<ABTestRecord[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [detail, setDetail] = useState<ABTestRecord | null>(null);
  const [form, setForm] = useState<ABTestForm>(() => emptyForm(products));
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [draftNote, setDraftNote] = useState('');
  const [draftConclusion, setDraftConclusion] = useState('');
  const [draftConclusionStatus, setDraftConclusionStatus] = useState('undecided');

  const selectedFormProduct = useMemo(
    () => visibleProducts.find(product => product.id === form.productId) || visibleProducts[0] || null,
    [visibleProducts, form.productId]
  );
  const selectedFormCountry = useMemo(
    () => selectedFormProduct?.countries?.find(country => country.id === form.countryId) || selectedFormProduct?.countries?.[0] || null,
    [selectedFormProduct, form.countryId]
  );
  const groupedTests = useMemo(() => {
    const productOrder = new Map(visibleProducts.map((product, index) => [getProductReelFarmCode(product), index]));
    const productByCode = new Map(visibleProducts.map(product => [getProductReelFarmCode(product), product]));
    const groups = new Map<string, {
      key: string;
      product?: Product;
      productName: string;
      tests: ABTestRecord[];
      countries: Map<string, {
        key: string;
        countryName: string;
        countryFlag: string;
        tests: ABTestRecord[];
      }>;
    }>();

    for (const test of tests) {
      const productCode = abTestProductCode(test);
      const countryCode = abTestCountryCode(test);
      const product = productByCode.get(productCode);
      const productKey = productCode || test.product_name || 'unknown';
      const productGroup = groups.get(productKey) || {
        key: productKey,
        product,
        productName: product?.name || test.product_name || productCode || 'Unknown Product',
        tests: [],
        countries: new Map()
      };
      const country = product?.countries?.find(item => getCountryReelFarmCode(item) === countryCode);
      const countryKey = countryCode || test.country_name || 'unknown';
      const countryGroup = productGroup.countries.get(countryKey) || {
        key: countryKey,
        countryName: country?.name || test.country_name || countryCode || 'Unknown Country',
        countryFlag: countryFlag(country || { id: countryKey, name: test.country_name || countryKey, reelFarmCode: countryCode }),
        tests: []
      };
      productGroup.tests.push(test);
      countryGroup.tests.push(test);
      productGroup.countries.set(countryKey, countryGroup);
      groups.set(productKey, productGroup);
    }

    return Array.from(groups.values())
      .sort((left, right) => {
        const leftIndex = productOrder.get(left.key) ?? 999;
        const rightIndex = productOrder.get(right.key) ?? 999;
        return leftIndex - rightIndex || left.productName.localeCompare(right.productName);
      })
      .map(group => {
        const countryOrder = new Map((group.product?.countries || []).map((country, index) => [getCountryReelFarmCode(country), index]));
        return {
          ...group,
          countries: Array.from(group.countries.values())
            .sort((left, right) => {
              const leftIndex = countryOrder.get(left.key) ?? 999;
              const rightIndex = countryOrder.get(right.key) ?? 999;
              return leftIndex - rightIndex || left.countryName.localeCompare(right.countryName);
            })
            .map(countryGroup => ({
              ...countryGroup,
              tests: [...countryGroup.tests].sort(compareTests)
            }))
        };
      });
  }, [tests, visibleProducts]);

  async function loadTests() {
    setLoading(true);
    setError('');
    try {
      const payload = await api.abTests();
      const nextTests = payload.tests || [];
      setTests(nextTests);
      setSelectedId(current => current || nextTests[0]?.id || '');
    } catch (loadError: unknown) {
      setError(getErrorMessage(loadError, 'AB Test 读取失败'));
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(testId: string) {
    if (!testId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    setError('');
    try {
      const payload = await api.abTest(testId);
      setDetail(payload.test);
      setDraftNote(payload.test.note || '');
      setDraftConclusion(payload.test.conclusion || '');
      setDraftConclusionStatus(payload.test.conclusion_status || 'undecided');
    } catch (loadError: unknown) {
      setError(getErrorMessage(loadError, 'AB Test 详情读取失败'));
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    if (active) void loadTests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  useEffect(() => {
    setForm(emptyForm(products));
  }, [products]);

  useEffect(() => {
    if (active && selectedId) void loadDetail(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, selectedId]);

  function updateForm(partial: Partial<ABTestForm>) {
    setForm(current => ({ ...current, ...partial }));
  }

  async function createTest() {
    if (!selectedFormProduct || !selectedFormCountry) return;
    setSaving(true);
    setError('');
    try {
      const productCode = getProductReelFarmCode(selectedFormProduct);
      const countryCode = getCountryReelFarmCode(selectedFormCountry);
      const payload = await api.createAbTest({
        name: form.name || `${selectedFormProduct.name} ${selectedFormCountry.name} AB Test`,
        product_code: productCode,
        country_code: countryCode,
        start_date: form.startDate,
        duration_days: form.durationDays,
        variable: form.variable,
        hypothesis: form.hypothesis,
        note: form.note
      });
      await loadTests();
      setSelectedId(payload.test.id);
      setDetail(payload.test);
      setShowCreate(false);
      setForm(emptyForm(products));
    } catch (saveError: unknown) {
      setError(getErrorMessage(saveError, 'AB Test 创建失败'));
    } finally {
      setSaving(false);
    }
  }

  async function saveReview() {
    if (!detail?.id) return;
    setSaving(true);
    setError('');
    try {
      const payload = await api.updateAbTest(detail.id, {
        note: draftNote,
        conclusion: draftConclusion,
        conclusion_status: draftConclusionStatus
      });
      setDetail(payload.test);
      await loadTests();
    } catch (saveError: unknown) {
      setError(getErrorMessage(saveError, 'AB Test 复盘保存失败'));
    } finally {
      setSaving(false);
    }
  }

  const comparison = detail?.comparison;
  const controlTotals = comparison?.control?.totals || {};
  const testTotals = comparison?.test?.totals || {};
  const delta = comparison?.delta || {};
  const cards = [
    metricCard('Total Posts', controlTotals.total_posts, testTotals.total_posts, delta.total_posts?.absolute, delta.total_posts?.percent),
    metricCard('Total View', controlTotals.total_views, testTotals.total_views, delta.total_views?.absolute, delta.total_views?.percent),
    metricCard('Avg View', controlTotals.avg_views, testTotals.avg_views, delta.avg_views?.absolute, delta.avg_views?.percent),
    metricCard('Onboarding', onboardingText(controlTotals), onboardingText(testTotals), delta.onboarding_unique?.absolute, delta.onboarding_unique?.percent),
    metricCard('转化', percent(controlTotals.conversion_rate), percent(testTotals.conversion_rate), delta.conversion_rate?.absolute, delta.conversion_rate?.percent)
  ];

  return (
    <section className="business-report-page ab-test-page">
      <WorkspaceHeader
        className="business-report-head"
        kicker="AB Test"
        title="AB Test"
        description="按产品和国家创建实验，自动对比测试区间与前置同周期业务日表现。"
        actions={(
          <div className="ab-test-actions">
            <button type="button" onClick={() => void loadTests()} disabled={loading}>{loading ? '刷新中...' : '刷新'}</button>
            <button type="button" className="primary" onClick={() => setShowCreate(value => !value)}>
              {showCreate ? '收起' : '+ 新建测试'}
            </button>
          </div>
        )}
      />

      {error ? <div className="growth-error">{error}</div> : null}
      {showCreate ? (
        <section className="ab-test-create">
          <div className="ab-test-create-grid">
            <label>
              测试名称
              <input value={form.name} placeholder="例如 DB Germany Hook Test" onChange={event => updateForm({ name: event.target.value })} />
            </label>
            <label>
              产品
              <select value={form.productId} onChange={event => {
                const nextProduct = visibleProducts.find(product => product.id === event.target.value) || visibleProducts[0];
                updateForm({ productId: event.target.value, countryId: nextProduct?.countries?.[0]?.id || '' });
              }}>
                {visibleProducts.map(product => <option value={product.id} key={product.id}>{product.name}</option>)}
              </select>
            </label>
            <label>
              国家
              <select value={selectedFormCountry?.id || ''} onChange={event => updateForm({ countryId: event.target.value })}>
                {(selectedFormProduct?.countries || []).map(country => (
                  <option value={country.id} key={country.id}>{country.name}</option>
                ))}
              </select>
            </label>
            <label>
              开始业务日
              <input type="date" value={form.startDate} onChange={event => updateForm({ startDate: event.target.value })} />
            </label>
            <label>
              持续天数
              <input type="number" min={1} max={90} value={form.durationDays} onChange={event => updateForm({ durationDays: Number(event.target.value) || 7 })} />
            </label>
            <label>
              测试变量
              <input value={form.variable} placeholder="Hook / CTA / 素材风格 / 批次" onChange={event => updateForm({ variable: event.target.value })} />
            </label>
          </div>
          <div className="ab-test-notes-grid">
            <label>
              测试假设
              <textarea value={form.hypothesis} placeholder="这次为什么测，预期提升哪个指标" onChange={event => updateForm({ hypothesis: event.target.value })} />
            </label>
            <label>
              备注
              <textarea value={form.note} placeholder="账号批次、执行注意事项、样本口径" onChange={event => updateForm({ note: event.target.value })} />
            </label>
          </div>
          <div className="ab-test-create-footer">
            <span>对照区间会自动取测试开始前相同天数。</span>
            <button type="button" onClick={createTest} disabled={saving || !selectedFormCountry}>{saving ? '创建中...' : '创建并计算'}</button>
          </div>
        </section>
      ) : null}

      <div className="ab-test-layout">
        <section className="ab-test-list">
          <div className="ab-test-section-head">
            <h2>实验列表</h2>
            <p>{tests.length} 个测试</p>
          </div>
          <div className="ab-test-grouped-list">
            {groupedTests.length ? groupedTests.map(group => (
              <div className="ab-test-product-group" key={group.key}>
                <div className="ab-test-product-head">
                  <ProductBadge product={group.product} name={group.productName} />
                  <div>
                    <strong>{group.productName}</strong>
                    <span>{group.countries.length} 个国家 · {group.tests.length} 个测试</span>
                  </div>
                </div>
                <div className="ab-test-country-groups">
                  {group.countries.map(countryGroup => (
                    <div className="ab-test-country-group" key={`${group.key}-${countryGroup.key}`}>
                      <div className="ab-test-country-head">
                        <span>{countryGroup.countryFlag}</span>
                        <strong>{countryGroup.countryName}</strong>
                        <em>{countryGroup.tests.length}</em>
                      </div>
                      <div className="ab-test-history-list">
                        {countryGroup.tests.map(test => (
                          <button
                            type="button"
                            className={`ab-test-history-row ${selectedId === test.id ? 'active' : ''}`}
                            onClick={() => setSelectedId(test.id)}
                            key={test.id}
                          >
                            <span className={`ab-test-status ${statusClass(test.status)}`}>{STATUS_LABELS[test.status || 'draft'] || test.status}</span>
                            <strong>{test.name}</strong>
                            <small>{rangeText(test, 'test')}</small>
                            <em>{CONCLUSION_LABELS[test.conclusion_status || 'undecided'] || '未判断'}</em>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )) : (
              <div className="ab-test-empty">还没有 AB Test。先新建一个测试。</div>
            )}
          </div>
        </section>

        <section className="ab-test-detail">
          {detailLoading ? <div className="growth-loading">正在实时计算测试数据...</div> : null}
          {detail ? (
            <>
              <div className="ab-test-detail-head">
                <div>
                  <span className={`ab-test-status ${statusClass(detail.status)}`}>{STATUS_LABELS[detail.status || 'draft'] || detail.status}</span>
                  <h2>{detail.name}</h2>
                  <p>{detail.product_name || detail.product_code} · {detail.country_name || detail.country_code}</p>
                </div>
                <div className="ab-test-periods">
                  <span>对照 {rangeText(detail, 'control')}</span>
                  <strong>测试 {rangeText(detail, 'test')}</strong>
                </div>
              </div>

              <div className="ab-test-comparison-grid">
                {cards.map(card => (
                  <article key={card.label}>
                    <span>{card.label}</span>
                    <div className="ab-test-compare-values">
                      <small>对照 <strong>{typeof card.control === 'string' ? card.control : numberMetric(card.control)}</strong></small>
                      <small>测试 <strong>{typeof card.test === 'string' ? card.test : numberMetric(card.test)}</strong></small>
                    </div>
                    <p className={(Number(card.percentDelta) || 0) >= 0 ? 'positive' : 'negative'}>
                      {card.label === '转化' ? signedNumber(card.delta as number | null) : signedNumber(card.delta as number | null)}
                      <em>{signedPercent(card.percentDelta)}</em>
                    </p>
                  </article>
                ))}
              </div>

              {(controlTotals.onboarding_scope === 'unavailable' || testTotals.onboarding_scope === 'unavailable') ? (
                <div className="ab-test-warning">
                  Mixpanel onboarding 事件暂未检测到国家字段，国家级 onboarding / 转化无法准确计算。请确认事件属性里是否有 country_code、country、market 等字段。
                </div>
              ) : null}

              <div className="ab-test-data-grid">
                <section>
                  <h3>对照区间每日数据</h3>
                  <ABTestDailyTable rows={comparison?.control?.rows || []} />
                </section>
                <section>
                  <h3>测试区间每日数据</h3>
                  <ABTestDailyTable rows={comparison?.test?.rows || []} />
                </section>
              </div>

              <div className="ab-test-review">
                <label>
                  测试备注
                  <textarea value={draftNote} onChange={event => setDraftNote(event.target.value)} />
                </label>
                <label>
                  结论状态
                  <select value={draftConclusionStatus} onChange={event => setDraftConclusionStatus(event.target.value)}>
                    {CONCLUSION_OPTIONS.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}
                  </select>
                </label>
                <label>
                  测试结论
                  <textarea value={draftConclusion} placeholder="有效/无效的原因，以及下一步扩量、停止、复测动作" onChange={event => setDraftConclusion(event.target.value)} />
                </label>
                <button type="button" onClick={saveReview} disabled={saving}>{saving ? '保存中...' : '保存复盘'}</button>
              </div>
            </>
          ) : (
            <div className="ab-test-empty">选择一个测试查看实时对比。</div>
          )}
        </section>
      </div>
    </section>
  );
}

function ABTestDailyTable({ rows }: { rows: ABTestDailyRow[] }) {
  return (
    <div className="ab-test-mini-table-wrap">
      <table className="ab-test-mini-table">
        <thead>
          <tr>
            <th>业务日</th>
            <th>Posts</th>
            <th>View</th>
            <th>Avg</th>
            <th>Onboarding</th>
            <th>转化</th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? rows.map(row => (
            <tr key={row.report_date}>
              <td>{compactDate(row.report_date)}</td>
              <td>{numberMetric(row.total_posts)}</td>
              <td>{numberMetric(row.total_views)}</td>
              <td>{numberMetric(row.avg_views)}</td>
              <td>{dailyOnboardingText(row)}</td>
              <td>{dailyConversionText(row)}</td>
            </tr>
          )) : (
            <tr><td colSpan={6}>暂无数据</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ProductBadge({ product, name }: { product?: Product; name: string }) {
  if (product?.logo) {
    return <img className="ab-test-product-logo" src={product.logo} alt="" />;
  }
  return <span className="ab-test-product-logo fallback">{initials(name)}</span>;
}
