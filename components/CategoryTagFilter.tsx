'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { getTagName } from './ReelFarmAccountCard';
import {
  accountTagStyle,
  generateUiId,
  tagCategories,
  tagsForCategory as getTagsForCategory,
  type TagFilterRow
} from './CountryAccountTagHelpers';

export function CategoryTagFilter({
  tagOptions,
  filters,
  onApply
}: {
  tagOptions: string[];
  filters: TagFilterRow[];
  onApply: (filters: TagFilterRow[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<TagFilterRow[]>(filters);
  const containerRef = useRef<HTMLDivElement>(null);
  const categories = useMemo(() => tagCategories(tagOptions), [tagOptions]);

  function openFilter() {
    if (open) {
      setOpen(false);
      return;
    }
    setDraft(filters.length ? filters : [{ id: generateUiId(), category: categories[0] || '', tags: [] }]);
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (target instanceof Node && containerRef.current?.contains(target)) return;
      setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  function updateRow(id: string, updater: (row: TagFilterRow) => TagFilterRow) {
    setDraft(previous => previous.map(row => row.id === id ? updater(row) : row));
  }

  const complete = draft.filter(row => row.category && row.tags.length);
  const canApply = complete.length === draft.length && draft.length > 0;
  const summary = filters.length
    ? `${filters.length} Tag Filter${filters.length > 1 ? 's' : ''}`
    : 'Tags';

  return (
    <div className="category-tag-filter" ref={containerRef}>
      <button className="text-input tag-filter-trigger" type="button" onClick={openFilter}>
        <span>{summary}</span>
        <span>⌄</span>
      </button>
      {open ? (
        <div className="tag-filter-popover">
          <div className="tag-filter-head">
            <div>
              <strong>Category + Tags</strong>
              <span>One category per row. Tags in that row are multi-select.</span>
            </div>
            <button type="button" onClick={() => setDraft(previous => [...previous, { id: generateUiId(), category: categories[0] || '', tags: [] }])}>+ Add</button>
          </div>
          <div className="tag-filter-rows">
            {draft.map(row => {
              const options = getTagsForCategory(tagOptions, row.category);
              return (
                <div className="tag-filter-row" key={row.id}>
                  <select
                    value={row.category}
                    onChange={event => updateRow(row.id, () => ({ ...row, category: event.target.value, tags: [] }))}
                  >
                    <option value="">Category</option>
                    {categories.map(category => <option value={category} key={category}>{category}</option>)}
                  </select>
                  <div className="tag-filter-tagbox">
                    <button className="tag-filter-tagbox-summary" type="button">
                      <span>{row.tags.length ? `${row.tags.length} selected` : 'Select tags'}</span>
                      <b>{row.tags.length}</b>
                      <span>⌄</span>
                    </button>
                    <div className="tag-filter-options">
                      {options.length ? options.map(tag => {
                        const checked = row.tags.includes(tag);
                        return (
                          <label key={tag}>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => updateRow(row.id, current => ({
                                ...current,
                                tags: checked ? current.tags.filter(item => item !== tag) : [...current.tags, tag]
                              }))}
                            />
                            <span style={accountTagStyle(tag)}>{getTagName(tag)}</span>
                          </label>
                        );
                      }) : <em>Select a category first</em>}
                    </div>
                  </div>
                  <button className="tag-filter-remove" type="button" onClick={() => setDraft(previous => previous.filter(item => item.id !== row.id))}>×</button>
                </div>
              );
            })}
          </div>
          <div className="tag-filter-actions">
            <button type="button" onClick={() => { onApply([]); setDraft([]); }}>Clear All</button>
            <span>{canApply ? 'Ready to apply filters.' : 'Select at least one tag for each selected category.'}</span>
            <button
              className="primary"
              type="button"
              disabled={!canApply}
              onClick={() => {
                onApply(complete);
                setOpen(false);
              }}
            >
              Apply Filters
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
