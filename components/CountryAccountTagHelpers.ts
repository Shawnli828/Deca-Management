'use client';

import type { AccountSummary, Country } from '@/lib/types';
import { getTagCategory, getTagName } from './ReelFarmAccountCard';

export type AccountTagRow = AccountSummary & { country: Country; tags?: string[]; issues?: string[] };
export type TagFilterRow = { id: string; category: string; tags: string[] };

type AccountTagStyle = {
  background: string;
  borderColor: string;
  color: string;
};

const ACCOUNT_TAG_PALETTE: AccountTagStyle[] = [
  { background: '#dbeafe', borderColor: '#93c5fd', color: '#1d4ed8' },
  { background: '#dcfce7', borderColor: '#86efac', color: '#15803d' },
  { background: '#fef3c7', borderColor: '#fbbf24', color: '#92400e' },
  { background: '#fce7f3', borderColor: '#f9a8d4', color: '#be185d' },
  { background: '#ede9fe', borderColor: '#c4b5fd', color: '#6d28d9' },
  { background: '#cffafe', borderColor: '#67e8f9', color: '#0e7490' }
];

export function nonIssueTags(tags: string[] = []) {
  return tags.filter(tag => getTagCategory(tag).toLowerCase() !== 'issue');
}

export function accountTagStyle(value: string) {
  let hash = 0;
  for (const char of getTagCategory(value)) hash = char.charCodeAt(0) + ((hash << 5) - hash);
  return ACCOUNT_TAG_PALETTE[Math.abs(hash) % ACCOUNT_TAG_PALETTE.length];
}

export function generateUiId() {
  return Math.random().toString(36).slice(2, 10);
}

export function tagCategories(tagOptions: string[]) {
  return Array.from(new Set(tagOptions.map(getTagCategory))).filter(Boolean).sort();
}

export function tagsForCategory(tagOptions: string[], category: string) {
  return tagOptions.filter(tag => getTagCategory(tag) === category);
}

export function categorySuggestions(availableTags: string[], categoryInput: string) {
  const normalizedCategory = categoryInput.trim().toLowerCase();
  return tagCategories(availableTags)
    .filter(category => !normalizedCategory || category.toLowerCase().includes(normalizedCategory));
}

export function tagNameSuggestions(tagOptions: string[], tagInput: string) {
  const normalizedTag = tagInput.trim().toLowerCase();
  return Array.from(new Set(tagOptions.map(getTagName)))
    .filter(tag => !normalizedTag || tag.toLowerCase().includes(normalizedTag))
    .sort((a, b) => a.localeCompare(b));
}
