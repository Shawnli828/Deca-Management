'use client';

import type { Product } from '@/lib/types';
import { normalizeProductFolder } from '@/lib/utils';
import { FormEvent, useEffect, useState } from 'react';

type ProductSettingsValue = {
  name: string;
  folder: string;
  logo?: string;
};

export function ProductSettingsModal({
  product,
  open,
  onClose,
  onSave,
  readLogo
}: {
  product: Product | null;
  open: boolean;
  onClose: () => void;
  onSave: (value: ProductSettingsValue) => Promise<void>;
  readLogo: (file: File) => Promise<string>;
}) {
  const [name, setName] = useState('');
  const [folder, setFolder] = useState('甲方');
  const [logo, setLogo] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!product || !open) return;
    setName(product.name || '');
    setFolder(normalizeProductFolder(product));
    setLogo(product.logo || '');
  }, [product, open]);

  if (!open || !product) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({ name: name.trim(), folder, logo });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="database-modal is-open" onClick={event => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="product-settings-panel" role="dialog" aria-modal="true" aria-labelledby="productSettingsTitle">
        <header className="database-header">
          <div>
            <h2 id="productSettingsTitle" className="database-title">产品设置</h2>
            <p className="database-subtitle">修改产品名称、所属文件夹和 Logo。</p>
          </div>
          <button className="icon-btn" type="button" onClick={onClose} title="关闭">×</button>
        </header>
        <form className="product-settings-body" onSubmit={submit}>
          <label className="settings-logo-picker">
            <span className="settings-logo-preview">
              {logo ? <img src={logo} alt="" /> : name.slice(0, 1)}
            </span>
            <span className="btn ghost">添加产品 Logo</span>
            <input
              className="product-logo-input"
              type="file"
              accept="image/*"
              onChange={async event => {
                const file = event.target.files?.[0];
                if (!file) return;
                setLogo(await readLogo(file));
                event.target.value = '';
              }}
            />
          </label>
          <label className="settings-field">
            <span>产品名称</span>
            <input className="text-input" value={name} onChange={event => setName(event.target.value)} />
          </label>
          <label className="settings-field">
            <span>产品所属</span>
            <select className="text-input" value={folder} onChange={event => setFolder(event.target.value)}>
              <option value="甲方">甲方</option>
              <option value="乙方">乙方</option>
            </select>
          </label>
          <div className="settings-actions">
            <button className="btn ghost" type="button" onClick={onClose}>取消</button>
            <button className="btn primary" type="submit" disabled={saving}>{saving ? '保存中...' : '保存设置'}</button>
          </div>
        </form>
      </section>
    </div>
  );
}
