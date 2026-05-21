'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { Country, Product, ProductKpis, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import { buildCountryAutomationPrefix, cardStateKey, getCountryReelFarmCode } from '@/lib/utils';
import { ProductKpiBoard } from './ProductKpiBoard';
import { composeTag, formatTagLabel, getTagCategory, getTagName, ReelFarmAccountCard, tagChipStyle } from './ReelFarmAccountCard';

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
  productTags
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
}) {
  const [editingTagCardKey, setEditingTagCardKey] = useState('');
  const prefix = buildCountryAutomationPrefix(product, country);
  const isSyncing = loadingPrefix === `country:${country.id}`;
  const displayedCreatorCount = Math.max(Number(result?.count) || 0, Number(country.creatorCount) || 0);
  const displayedMaterialCount = Number(country.materialCount) || 0;
  const editingTagCard = editingTagCardKey ? result?.cards?.find(card => cardStateKey(card) === editingTagCardKey) : null;

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
                        onRemoveTag={onRemoveTag}
                        onOpenTagEditor={card => setEditingTagCardKey(cardStateKey(card))}
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
      {editingTagCard ? (
        <CreatorTagEditorModal
          card={editingTagCard}
          availableTags={productTags}
          onClose={() => setEditingTagCardKey('')}
          onAddTag={onAddTag}
          onRemoveTag={onRemoveTag}
        />
      ) : null}
    </section>
  );
}

function CreatorTagEditorModal({
  card,
  availableTags,
  onClose,
  onAddTag,
  onRemoveTag
}: {
  card: ReelFarmCard;
  availableTags: string[];
  onClose: () => void;
  onAddTag: (card: ReelFarmCard, tag: string) => void;
  onRemoveTag: (card: ReelFarmCard, tag: string) => void;
}) {
  const [mounted, setMounted] = useState(false);
  const [categoryInput, setCategoryInput] = useState('');
  const [tagInput, setTagInput] = useState('');
  const key = cardStateKey(card);
  const tags = card.tags || [];
  const categories = Array.from(new Set(availableTags.map(getTagCategory).filter(Boolean)));
  const tagOptions = availableTags.filter(tag => !categoryInput.trim() || getTagCategory(tag).toLowerCase() === categoryInput.trim().toLowerCase());

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <div className="tag-editor-backdrop" onClick={onClose}>
      <div className="tag-editor-modal" onClick={event => event.stopPropagation()}>
        <button className="tag-editor-close" type="button" onClick={onClose}>×</button>
        <h3>Edit Creator Tags</h3>
        <div className="tag-editor-section-title">Add Tag</div>
        <div className="tag-editor-row">
          <label className="tag-editor-field">
            <span>⌕</span>
            <input
              value={categoryInput}
              onChange={event => setCategoryInput(event.target.value)}
              placeholder="Category (search or type new)"
              list={`tag-categories-${key}`}
            />
            <datalist id={`tag-categories-${key}`}>
              {categories.map(category => <option value={category} key={category} />)}
            </datalist>
          </label>
          <label className="tag-editor-field">
            <span>⌕</span>
            <input
              value={tagInput}
              onChange={event => setTagInput(event.target.value)}
              placeholder={categoryInput.trim() ? 'Select or type tag' : 'Select category first...'}
              list={`tag-options-${key}`}
            />
            <datalist id={`tag-options-${key}`}>
              {tagOptions.map(option => <option value={getTagName(option)} key={option} />)}
            </datalist>
          </label>
          <button
            className="tag-editor-add"
            type="button"
            disabled={!categoryInput.trim() || !tagInput.trim()}
            onClick={() => {
              const nextTag = composeTag(categoryInput, tagInput);
              onAddTag(card, nextTag);
              setTagInput('');
            }}
          >
            + Add
          </button>
        </div>
        <div className="tag-editor-current">
          {tags.length ? tags.map(tag => (
            <button className="creator-tag-chip" style={tagChipStyle(tag)} type="button" key={tag} onClick={() => onRemoveTag(card, tag)}>
              {formatTagLabel(tag)} ×
            </button>
          )) : <span className="creator-tag-empty">No tags yet</span>}
        </div>
        <div className="tag-editor-actions">
          <button className="tag-editor-cancel" type="button" onClick={onClose}>Cancel</button>
          <button className="tag-editor-save" type="button" onClick={onClose}>Save Tags</button>
        </div>
      </div>
    </div>,
    document.body
  );
}
