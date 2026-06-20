import type { AccountSummary, Country } from '../types';

export type AccountTagRow = AccountSummary & { country: Country; tags?: string[]; issues?: string[] };
export type TagFilterRow = { id: string; category: string; tags: string[] };
