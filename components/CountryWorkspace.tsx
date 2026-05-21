'use client';

import { useState } from 'react';
import type { Country, Product, ProductKpis, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import { buildCountryAutomationPrefix, cardStateKey, getCountryReelFarmCode } from '@/lib/utils';
import { ProductKpiBoard } from './ProductKpiBoard';
import { ReelFarmAccountCard } from './ReelFarmAccountCard';

export function CountryWorkspace({
  product,
  country,
  kpis,
  result,
  days,
  loadingPrefix,
  expandedCards,
  postLoading,
  slideIndexes,
  onBack,
  onDays,
  onSync,
  onToggleCard,
  onPage,
  onMoveSlide,
  onAddTag,
  onRemoveTag,
  productTags,
  onCreateTag
}: {
  product: Product;
  country: Country;
  kpis?: ProductKpis | null;
  result?: ReelFarmResult;
  days: number;
  loadingPrefix: string;
  expandedCards: Record<string, boolean>;
  postLoading: Record<string, boolean>;
  slideIndexes: Record<string, number>;
  onBack: () => void;
  onDays: (days: number) => void;
  onSync: () => void;
  onToggleCard: (key: string) => void;
  onPage: (key: string, direction: number) => void;
  onMoveSlide: (videoId: string, direction: number, total: number) => void;
  onAddTag: (card: ReelFarmCard, tag: string) => void;
  onRemoveTag: (card: ReelFarmCard, tag: string) => void;
  productTags: string[];
  onCreateTag: (tag: string) => Promise<void>;
}) {
  const [tagInput, setTagInput] = useState('');
  const [tagSaving, setTagSaving] = useState(false);
  const [tagError, setTagError] = useState('');
  const prefix = buildCountryAutomationPrefix(product, country);
  const isSyncing = loadingPrefix === `country:${country.id}`;
  const displayedCreatorCount = Math.max(Number(result?.count) || 0, Number(country.creatorCount) || 0);
  const displayedMaterialCount = Number(country.materialCount) || 0;

  return (
    <section className="page active">
      <nav className="breadcrumbs">
        <button className="crumb-btn" type="button" onClick={onBack}>产品总览 / {product.name}</button>
        <span>/</span>
        <strong>{country.name}</strong>
      </nav>
      <ProductKpiBoard kpis={kpis} />
      <div className="country-workspace">
        <aside className="country-sidebar">
          <div className="country-sidebar-head">
            <div className="country-title-row">
              <h2 className="country-sidebar-title">{country.name} 素材库</h2>
              <button className="btn primary" type="button" onClick={onSync} disabled={isSyncing}>{isSyncing ? '同步中...' : '同步当前区'}</button>
            </div>
            <div className="context-meta">{product.name} · {displayedCreatorCount} 个账号 · {displayedMaterialCount} 个素材</div>
            <div className="time-filter" role="group" aria-label="ReelFarm 时间维度">
              <span className="time-filter-label">观察窗口</span>
              <div className="time-filter-options">
                {[7, 14, 30].map(option => (
                  <button className={`time-filter-btn ${days === option ? 'active' : ''}`} type="button" key={option} onClick={() => onDays(option)}>{option}day</button>
                ))}
              </div>
            </div>
          </div>
          <div className="country-sidebar-fields">
            <form className="country-tag-form" onSubmit={async event => {
              event.preventDefault();
              if (!tagInput.trim()) return;
              setTagSaving(true);
              setTagError('');
              try {
                await onCreateTag(tagInput.trim());
                setTagInput('');
              } catch (error: any) {
                setTagError(error?.message || 'Tag 添加失败');
              } finally {
                setTagSaving(false);
              }
            }}>
              <span className="field-label">Tag</span>
              <div className="country-tag-input-row">
                <input className="text-input" value={tagInput} onChange={event => setTagInput(event.target.value)} placeholder="写一个 tag" disabled={tagSaving} />
                <button className="creator-tag-add" type="submit" title="添加" disabled={tagSaving}>+</button>
              </div>
              {tagError ? <span className="country-tag-error">{tagError}</span> : null}
              <div className="country-tag-pool">
                {productTags.length ? productTags.map(tag => (
                  <span className="creator-tag-chip" key={tag}>#{tag}</span>
                )) : <span className="country-tag-empty">暂无 tag</span>}
              </div>
            </form>
            <label>
              <span className="field-label">当前国家/地区</span>
              <input className="text-input" value={country.name || ''} readOnly />
            </label>
            <label>
              <span className="field-label">ReelFarm 国家代码</span>
              <input className="text-input" value={getCountryReelFarmCode(country)} readOnly />
            </label>
          </div>
        </aside>
        <section className="country-main">
          <section className="reelfarm-format">
            <div className="reelfarm-format-head">
              <div>
                <span className="automation-prefix">{prefix}</span>
                <div className="item-meta">国家/地区素材池 · 暂不按 Topic / Format 分类</div>
                {country.reelFarmSyncedAt ? <div className="item-meta">上次同步：{country.reelFarmSyncedAt}</div> : null}
              </div>
            </div>
            {isSyncing ? (
              <div className="empty-state"><div className="empty-title">正在从 ReelFarm 拉取这个国家/地区的全部素材...</div></div>
            ) : result?.loading ? (
              <div className="empty-state"><div className="empty-title">Loading accounts...</div></div>
            ) : result?.error ? (
              <div className="empty-state"><div className="empty-title">同步失败</div><div>{result.error}</div></div>
            ) : result?.cards?.length ? (
              <div className="creator-table">
                <div className="creator-table-head">
                  <div>Creator ↕</div>
                  <div></div>
                  <div>Posts ↕</div>
                  <div>Views ↕</div>
                  <div>Likes ↕</div>
                  <div>Comments ↕</div>
                  <div>Shares ↕</div>
                  <div>% Engagement ↕</div>
                  <div></div>
                </div>
                <div className="reelfarm-cards">
                  {result.cards.map(card => {
                    const key = cardStateKey(card);
                    return (
                      <ReelFarmAccountCard
                        key={key}
                        card={card}
                        isOpen={Boolean(expandedCards[key])}
                        isLoading={Boolean(postLoading[key])}
                        slideIndexes={slideIndexes}
                        onToggle={onToggleCard}
                        onPage={onPage}
                        onMoveSlide={onMoveSlide}
                        onAddTag={onAddTag}
                        onRemoveTag={onRemoveTag}
                        availableTags={productTags}
                      />
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="empty-state"><div className="empty-title">Loading accounts...</div></div>
            )}
          </section>
        </section>
      </div>
    </section>
  );
}
