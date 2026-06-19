'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { ReelFarmCard } from '@/lib/types';
import {
  composeTag,
  formatTagLabel,
  getTagCategory,
  getTagName,
  tagChipStyle
} from '@/lib/tagUtils';
import { cardStateKey } from '@/lib/utils';

export function CreatorTagEditorModal({
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
