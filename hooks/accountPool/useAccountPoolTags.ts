'use client';

import { useMemo, useState, type Dispatch, type SetStateAction } from 'react';
import { api } from '@/lib/api';
import type { AccountPoolRow } from '@/lib/domain/accountPool';
import { formatTagLabel } from '@/lib/tagUtils';
import type { TagFilterRow } from '@/lib/domain/accountTags';
import {
  addTagToRows,
  removeProductTagFromFilters,
  removeProductTagFromRows,
  removeTagFromRows
} from '../accountPoolStateHelpers';

type UseAccountPoolTagsOptions = {
  productCode: string;
  rows: AccountPoolRow[];
  setRows: Dispatch<SetStateAction<AccountPoolRow[]>>;
  setProductTagOptions: Dispatch<SetStateAction<string[]>>;
  setTagFilters: Dispatch<SetStateAction<TagFilterRow[]>>;
};

export function useAccountPoolTags({
  productCode,
  rows,
  setRows,
  setProductTagOptions,
  setTagFilters
}: UseAccountPoolTagsOptions) {
  const [editingTagAccountId, setEditingTagAccountId] = useState('');
  const editingTagRow = useMemo(
    () => editingTagAccountId ? rows.find(row => row.account_id === editingTagAccountId) || null : null,
    [editingTagAccountId, rows]
  );

  async function addAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    const nextTag = tag.trim();
    if (!accountId || !nextTag) return;
    const productTagsPayload = await api.createProductTag(productCode, nextTag);
    setProductTagOptions(productTagsPayload.tags || []);
    const payload = await api.addAccountTag(accountId, nextTag);
    setRows(previous => addTagToRows(previous, accountId, payload.tag));
  }

  async function removeAccountTag(row: AccountPoolRow, tag: string) {
    const accountId = String(row.account_id || '').trim();
    if (!accountId || !tag) return;
    await api.deleteAccountTag(accountId, tag);
    setRows(previous => removeTagFromRows(previous, accountId, tag));
  }

  async function deleteProductTagOption(tag: string) {
    const nextTag = tag.trim();
    if (!productCode || !nextTag) return;
    const confirmed = window.confirm(`删除 ${formatTagLabel(nextTag)} 吗？这个 Tag 会从当前产品所有账号上移除。`);
    if (!confirmed) return;
    const payload = await api.deleteProductTag(productCode, nextTag, true);
    const deletedTag = (payload.deleted_tag || nextTag).toLowerCase();
    setProductTagOptions(payload.tags || []);
    setRows(previous => removeProductTagFromRows(previous, deletedTag));
    setTagFilters(previous => removeProductTagFromFilters(previous, deletedTag));
  }

  return {
    editingTagRow,
    setEditingTagAccountId,
    addAccountTag,
    removeAccountTag,
    deleteProductTagOption
  };
}
