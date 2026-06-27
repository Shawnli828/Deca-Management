'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useAutomationCoverage } from '@/hooks/useAutomationCoverage';
import type { AutomationCoverageCountry, AutomationCoverageProduct, AutomationCoverageStatus } from '@/lib/types';

const STATUS_COPY: Record<AutomationCoverageStatus, string> = {
  unset: '未设目标',
  achieved: '达标',
  ready_to_cover: 'Ready 可补齐',
  warming_to_cover: '养号补齐中',
  behind: '不足',
  critical: '严重不足'
};

const STATUS_TONE: Record<AutomationCoverageStatus, string> = {
  unset: 'neutral',
  achieved: 'success',
  ready_to_cover: 'ready',
  warming_to_cover: 'warming',
  behind: 'behind',
  critical: 'critical'
};

function formatNumber(value: number | null | undefined) {
  return new Intl.NumberFormat('en-US').format(Number(value || 0));
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '未设';
  return `${Number(value).toFixed(1)}%`;
}

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function targetKey(productCode: string, countryCode: string) {
  return `${productCode}:${countryCode}`;
}

function productInitial(product: AutomationCoverageProduct) {
  return (product.product_name || product.product_code || '?').slice(0, 1).toUpperCase();
}

function progressWidth(value: number | null | undefined) {
  return `${Math.max(0, Math.min(100, Number(value || 0)))}%`;
}

function statusCopy(status: string) {
  return STATUS_COPY[status as AutomationCoverageStatus] || status || '未知';
}

function StatusPill({ status }: { status: string }) {
  const tone = STATUS_TONE[status as AutomationCoverageStatus] || 'neutral';
  return <span className={`automation-status-pill ${tone}`}>{statusCopy(status)}</span>;
}

function ProductLogo({ product }: { product: AutomationCoverageProduct }) {
  if (product.logo_url) {
    return <img className="automation-product-logo-img" src={product.logo_url} alt={`${product.product_name} logo`} />;
  }
  return <span className="automation-product-logo-fallback">{productInitial(product)}</span>;
}

type WarmupModalState = {
  productCode: string;
  countryCode: string;
  batchName: string;
  accountCount: string;
  warmupStartDate: string;
  warmupDays: string;
  note: string;
};

const EMPTY_WARMUP_FORM: WarmupModalState = {
  productCode: '',
  countryCode: '',
  batchName: '',
  accountCount: '10',
  warmupStartDate: todayValue(),
  warmupDays: '7',
  note: ''
};

type ProductCardProps = {
  product: AutomationCoverageProduct;
  targetEdits: Record<string, string>;
  saving: boolean;
  onTargetChange: (productCode: string, countryCode: string, value: string) => void;
  onTargetSave: (product: AutomationCoverageProduct, country: AutomationCoverageCountry) => Promise<void>;
  onOpenWarmup: (product: AutomationCoverageProduct) => void;
};

function ProductCard({
  product,
  targetEdits,
  saving,
  onTargetChange,
  onTargetSave,
  onOpenWarmup
}: ProductCardProps) {
  const completion = product.completion_rate ?? 0;
  return (
    <article className="automation-product-card">
      <header className="automation-product-header">
        <div className="automation-product-title">
          <span className="automation-product-logo"><ProductLogo product={product} /></span>
          <div>
            <h2>{product.product_name}</h2>
            <p>{product.countries.length} 个国家 · RF Active Automation</p>
          </div>
        </div>
        <button className="btn ghost automation-card-action" type="button" onClick={() => onOpenWarmup(product)}>
          + 登记养号
        </button>
      </header>

      <div className="automation-product-stats" aria-label={`${product.product_name} automation summary`}>
        <div className="automation-stat featured">
          <span>Active / Target</span>
          <strong>{formatNumber(product.active_count)} / {product.target_count ? formatNumber(product.target_count) : '未设'}</strong>
          <div className="automation-mini-bar"><i style={{ width: progressWidth(completion) }} /></div>
        </div>
        <div className="automation-stat">
          <span>Gap</span>
          <strong>{product.target_count ? formatNumber(product.gap_count) : '未设'}</strong>
        </div>
        <div className="automation-stat">
          <span>养号中</span>
          <strong>{formatNumber(product.warming_count)}</strong>
        </div>
        <div className="automation-stat">
          <span>Ready</span>
          <strong>{formatNumber(product.ready_count)}</strong>
        </div>
        <div className="automation-stat">
          <span>覆盖率</span>
          <strong>{formatPercent(product.completion_rate)}</strong>
        </div>
      </div>

      <div className="automation-country-table-wrap">
        <table className="automation-country-table">
          <thead>
            <tr>
              <th>国家</th>
              <th>Active</th>
              <th>Target</th>
              <th>Coverage</th>
              <th>Gap</th>
              <th>养号</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {product.countries.map(country => {
              const key = targetKey(product.product_code, country.country_code);
              const targetValue = targetEdits[key] ?? (country.target_count ? String(country.target_count) : '');
              const gapPercent = country.target_count ? Math.min(100, (country.gap_count / country.target_count) * 100) : 0;
              return (
                <tr key={key}>
                  <td>
                    <div className="automation-country-name">
                      <strong>{country.country_name}</strong>
                      <span>{country.country_code}</span>
                    </div>
                  </td>
                  <td className="numeric">{formatNumber(country.active_count)}</td>
                  <td>
                    <input
                      className="automation-target-input"
                      inputMode="numeric"
                      min={0}
                      type="number"
                      value={targetValue}
                      placeholder="目标"
                      onChange={event => onTargetChange(product.product_code, country.country_code, event.target.value)}
                    />
                  </td>
                  <td>
                    <div className="automation-bar-cell">
                      <div className="automation-progress coverage"><i style={{ width: progressWidth(country.completion_rate) }} /></div>
                      <span>{formatPercent(country.completion_rate)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="automation-bar-cell">
                      <div className="automation-progress gap"><i style={{ width: progressWidth(gapPercent) }} /></div>
                      <span>{country.target_count ? formatNumber(country.gap_count) : '未设'}</span>
                    </div>
                  </td>
                  <td>
                    <div className="automation-warmup-cell">
                      <div className="automation-warmup-line">
                        <strong>{formatNumber(country.warming_count)}</strong>
                        <span>{country.next_ready_date ? `${country.next_ready_date} Ready` : '无批次'}</span>
                      </div>
                      <div className="automation-progress warmup"><i style={{ width: progressWidth(country.warmup_progress) }} /></div>
                    </div>
                  </td>
                  <td><StatusPill status={country.status} /></td>
                  <td className="row-action">
                    <button className="btn ghost small" type="button" disabled={saving} onClick={() => onTargetSave(product, country)}>
                      保存
                    </button>
                  </td>
                </tr>
              );
            })}
            {!product.countries.length ? (
              <tr>
                <td colSpan={8}>
                  <div className="automation-empty-row">暂无国家 automation 数据。</div>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {product.warmups.length ? (
        <div className="automation-warmup-list">
          <div className="automation-section-label">养号批次</div>
          <div className="automation-warmup-grid">
            {product.warmups.slice(0, 6).map(batch => (
              <div className="automation-warmup-chip" key={batch.id}>
                <div>
                  <strong>{batch.batch_name || `${batch.country_code} 批次`}</strong>
                  <span>{batch.country_code} · {formatNumber(batch.account_count)} 个 · {batch.remaining_days ?? 0} 天</span>
                </div>
                <div className="automation-progress warmup"><i style={{ width: progressWidth(batch.progress) }} /></div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}

export function AutomationCoveragePage({ active }: { active: boolean }) {
  const { payload, loading, saving, error, loadCoverage, saveTarget, createWarmup } = useAutomationCoverage({ enabled: active });
  const [targetEdits, setTargetEdits] = useState<Record<string, string>>({});
  const [warmupForm, setWarmupForm] = useState<WarmupModalState | null>(null);

  const products = payload?.products || [];
  const selectedWarmupProduct = useMemo(
    () => products.find(product => product.product_code === warmupForm?.productCode) || null,
    [products, warmupForm?.productCode]
  );

  function handleTargetChange(productCode: string, countryCode: string, value: string) {
    setTargetEdits(current => ({ ...current, [targetKey(productCode, countryCode)]: value }));
  }

  async function handleTargetSave(product: AutomationCoverageProduct, country: AutomationCoverageCountry) {
    const key = targetKey(product.product_code, country.country_code);
    const nextValue = Number(targetEdits[key] ?? country.target_count ?? 0);
    await saveTarget({
      productCode: product.product_code,
      countryCode: country.country_code,
      targetCount: Number.isFinite(nextValue) ? Math.max(0, nextValue) : 0,
      note: country.target_note || ''
    });
    setTargetEdits(current => {
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function openWarmup(product: AutomationCoverageProduct) {
    setWarmupForm({
      ...EMPTY_WARMUP_FORM,
      productCode: product.product_code,
      countryCode: product.countries[0]?.country_code || ''
    });
  }

  async function handleWarmupSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!warmupForm) return;
    await createWarmup({
      productCode: warmupForm.productCode,
      countryCode: warmupForm.countryCode,
      batchName: warmupForm.batchName,
      accountCount: Math.max(1, Number(warmupForm.accountCount || 0)),
      warmupStartDate: warmupForm.warmupStartDate || todayValue(),
      warmupDays: Math.max(1, Number(warmupForm.warmupDays || 7)),
      note: warmupForm.note
    });
    setWarmupForm(null);
  }

  return (
    <section className="automation-coverage-page">
      <header className="automation-hero">
        <div>
          <span className="automation-kicker">Automation Coverage</span>
          <h1>自动化覆盖</h1>
          <p>按甲方产品和国家管理 RF active automation、目标数量与手动登记的养号倒计时。</p>
        </div>
        <div className="automation-hero-actions">
          <span className="status-pill">{loading ? '加载中' : `${products.length} 个甲方产品`}</span>
          <button className="btn ghost" type="button" onClick={loadCoverage} disabled={loading || saving}>刷新</button>
        </div>
      </header>

      {error ? <div className="automation-error">{error}</div> : null}

      <div className="automation-product-wall">
        {products.map(product => (
          <ProductCard
            key={product.product_code}
            product={product}
            targetEdits={targetEdits}
            saving={saving}
            onTargetChange={handleTargetChange}
            onTargetSave={handleTargetSave}
            onOpenWarmup={openWarmup}
          />
        ))}
        {!loading && !products.length ? (
          <div className="automation-empty">
            <h2>暂无 RF automation 覆盖数据</h2>
            <p>先同步 ReelFarm 产品和国家数据后，这里会按甲方产品展示 active automation 数量。</p>
          </div>
        ) : null}
      </div>

      {warmupForm && selectedWarmupProduct ? (
        <div className="automation-modal-backdrop" role="presentation" onMouseDown={() => setWarmupForm(null)}>
          <form className="automation-modal" onSubmit={handleWarmupSubmit} onMouseDown={event => event.stopPropagation()}>
            <header>
              <div>
                <span className="automation-kicker">Warm-up Batch</span>
                <h2>登记养号</h2>
                <p>{selectedWarmupProduct.product_name}</p>
              </div>
              <button className="automation-modal-close" type="button" onClick={() => setWarmupForm(null)} aria-label="关闭">×</button>
            </header>
            <div className="automation-form-grid">
              <label>
                国家
                <select
                  value={warmupForm.countryCode}
                  onChange={event => setWarmupForm(current => current ? { ...current, countryCode: event.target.value } : current)}
                  required
                >
                  {selectedWarmupProduct.countries.map(country => (
                    <option value={country.country_code} key={country.country_code}>{country.country_name}</option>
                  ))}
                </select>
              </label>
              <label>
                数量
                <input
                  type="number"
                  min={1}
                  value={warmupForm.accountCount}
                  onChange={event => setWarmupForm(current => current ? { ...current, accountCount: event.target.value } : current)}
                  required
                />
              </label>
              <label>
                开始日期
                <input
                  type="date"
                  value={warmupForm.warmupStartDate}
                  onChange={event => setWarmupForm(current => current ? { ...current, warmupStartDate: event.target.value } : current)}
                  required
                />
              </label>
              <label>
                养号天数
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={warmupForm.warmupDays}
                  onChange={event => setWarmupForm(current => current ? { ...current, warmupDays: event.target.value } : current)}
                  required
                />
              </label>
              <label className="span-2">
                批次名称
                <input
                  value={warmupForm.batchName}
                  placeholder="例如 GE 6月第二批"
                  onChange={event => setWarmupForm(current => current ? { ...current, batchName: event.target.value } : current)}
                />
              </label>
              <label className="span-2">
                备注
                <textarea
                  value={warmupForm.note}
                  placeholder="账号来源、负责人、注意事项"
                  onChange={event => setWarmupForm(current => current ? { ...current, note: event.target.value } : current)}
                />
              </label>
            </div>
            <footer>
              <button className="btn ghost" type="button" onClick={() => setWarmupForm(null)}>取消</button>
              <button className="btn primary" type="submit" disabled={saving}>{saving ? '保存中' : '保存批次'}</button>
            </footer>
          </form>
        </div>
      ) : null}
    </section>
  );
}
