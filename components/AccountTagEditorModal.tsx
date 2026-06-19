'use client';

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { composeTag, formatTagLabel, getTagCategory, getTagName } from './ReelFarmAccountCard';
import {
  accountTagStyle,
  categorySuggestions as getCategorySuggestions,
  nonIssueTags,
  tagNameSuggestions,
  type AccountTagRow
} from './CountryAccountTagHelpers';

export function AccountTagEditorModal({
  row,
  availableTags,
  fixedCategory,
  title = 'Edit Creator Tags',
  emptyLabel = 'No tags yet',
  sectionTitle = 'Add Tag',
  saveLabel = 'Save Tags',
  onClose,
  onAddTag,
  onRemoveTag,
  onDeleteProductTag
}: {
  row: AccountTagRow;
  availableTags: string[];
  fixedCategory?: string;
  title?: string;
  emptyLabel?: string;
  sectionTitle?: string;
  saveLabel?: string;
  onClose: () => void;
  onAddTag: (row: AccountTagRow, tag: string) => void | Promise<void>;
  onRemoveTag: (row: AccountTagRow, tag: string) => void | Promise<void>;
  onDeleteProductTag?: (tag: string) => void | Promise<void>;
}) {
  const [mounted, setMounted] = useState(false);
  const [categoryInput, setCategoryInput] = useState(fixedCategory || '');
  const [tagInput, setTagInput] = useState('');
  const [categoryMenuOpen, setCategoryMenuOpen] = useState(false);
  const [tagMenuOpen, setTagMenuOpen] = useState(false);
  const categoryMenuRef = useRef<HTMLDivElement>(null);
  const tagMenuRef = useRef<HTMLDivElement>(null);
  const tags = fixedCategory
    ? (row.tags || []).filter(tag => getTagCategory(tag).toLowerCase() === fixedCategory.toLowerCase())
    : nonIssueTags(row.tags);
  const normalizedCategory = categoryInput.trim().toLowerCase();
  const tagOptions = availableTags.filter(tag => !normalizedCategory || getTagCategory(tag).toLowerCase() === normalizedCategory);
  const categorySuggestions = getCategorySuggestions(availableTags, categoryInput);
  const tagSuggestions = tagNameSuggestions(tagOptions, tagInput);
  const canAddTag = Boolean(categoryInput.trim() && tagInput.trim());

  function commitTag() {
    if (!canAddTag) return;
    onAddTag(row, composeTag(categoryInput, tagInput));
    setTagInput('');
    setTagMenuOpen(false);
  }

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!categoryMenuRef.current?.contains(target)) setCategoryMenuOpen(false);
      if (!tagMenuRef.current?.contains(target)) setTagMenuOpen(false);
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <div className="tag-editor-backdrop" onClick={onClose}>
      <div className="tag-editor-modal" onClick={event => event.stopPropagation()}>
        <button className="tag-editor-close" type="button" onClick={onClose}>×</button>
        <h3>{title}</h3>
        <div className="tag-editor-current">
          {tags.length ? tags.map(tag => (
            <button className="creator-tag-chip" style={accountTagStyle(tag)} type="button" key={tag} onClick={() => onRemoveTag(row, tag)}>
              {fixedCategory ? getTagName(tag) : formatTagLabel(tag)} ×
            </button>
          )) : <span className="creator-tag-empty">{emptyLabel}</span>}
        </div>
        <div className="tag-editor-section-title">{sectionTitle}</div>
        <div className="tag-editor-row">
          {!fixedCategory ? (
            <div className="tag-editor-combobox" ref={categoryMenuRef}>
              <div className="tag-editor-field">
                <span>⌕</span>
                <input
                  value={categoryInput}
                  onFocus={() => setCategoryMenuOpen(true)}
                  onChange={event => {
                    setCategoryInput(event.target.value);
                    setTagInput('');
                    setCategoryMenuOpen(true);
                  }}
                  placeholder="Select or type category"
                  autoComplete="off"
                />
                <button
                  className="tag-editor-menu-toggle"
                  type="button"
                  aria-label="选择 Category"
                  onClick={() => setCategoryMenuOpen(previous => !previous)}
                >
                  ⌄
                </button>
              </div>
              {categoryMenuOpen ? (
                <div className="tag-editor-list">
                  {categorySuggestions.length ? categorySuggestions.map(category => (
                    <button
                      type="button"
                      key={category}
                      onClick={() => {
                        setCategoryInput(category);
                        setTagInput('');
                        setCategoryMenuOpen(false);
                        setTagMenuOpen(true);
                      }}
                    >
                      {category}
                    </button>
                  )) : <span className="tag-editor-list-empty">No existing category. Type to create new.</span>}
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="tag-editor-combobox" ref={tagMenuRef}>
            <div className="tag-editor-field">
              <span>⌕</span>
              <input
                value={tagInput}
                onFocus={() => {
                  if (categoryInput.trim()) setTagMenuOpen(true);
                }}
                onChange={event => {
                  setTagInput(event.target.value);
                  setTagMenuOpen(Boolean(categoryInput.trim()));
                }}
                onKeyDown={event => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    commitTag();
                  }
                }}
                placeholder={categoryInput.trim() ? 'Select or type tag' : 'Select category first...'}
                autoComplete="off"
                disabled={!categoryInput.trim()}
              />
              <button
                className="tag-editor-menu-toggle"
                type="button"
                aria-label="选择 Tag"
                disabled={!categoryInput.trim()}
                onClick={() => setTagMenuOpen(previous => categoryInput.trim() ? !previous : false)}
              >
                ⌄
              </button>
            </div>
            {tagMenuOpen ? (
              <div className="tag-editor-list">
                {tagSuggestions.length ? tagSuggestions.map(tag => {
                  const fullTag = tagOptions.find(option => getTagName(option).toLowerCase() === tag.toLowerCase()) || composeTag(categoryInput, tag);
                  return (
                    <div className="tag-editor-option-row" key={tag}>
                      <button
                        className="tag-editor-option-select"
                        type="button"
                        onClick={() => {
                          setTagInput(tag);
                          setTagMenuOpen(false);
                        }}
                      >
                        {tag}
                      </button>
                      {onDeleteProductTag ? (
                        <button
                          className="tag-editor-option-delete"
                          type="button"
                          aria-label={`删除 ${formatTagLabel(fullTag)}`}
                          title="从当前产品删除这个 Tag"
                          onClick={event => {
                            event.stopPropagation();
                            onDeleteProductTag(fullTag);
                            if (tagInput.toLowerCase() === tag.toLowerCase()) setTagInput('');
                          }}
                        >
                          ×
                        </button>
                      ) : null}
                    </div>
                  );
                }) : <span className="tag-editor-list-empty">No existing tag. Type to create new.</span>}
              </div>
            ) : null}
          </div>
          <button
            className="tag-editor-add"
            type="button"
            disabled={!canAddTag}
            onClick={commitTag}
          >
            + Add
          </button>
        </div>
        <div className="tag-editor-actions">
          <button className="tag-editor-cancel" type="button" onClick={onClose}>Cancel</button>
          <button className="tag-editor-save" type="button" onClick={onClose}>{saveLabel}</button>
        </div>
      </div>
    </div>,
    document.body
  );
}
