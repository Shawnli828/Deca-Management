'use client';

import type { Country, Product } from '@/lib/types';
import { codeFromName } from '@/lib/utils';
import { FormEvent, useEffect, useState } from 'react';

export function CountrySettingsModal({
  product,
  open,
  onClose,
  onSave
}: {
  product: Product | null;
  open: boolean;
  onClose: () => void;
  onSave: (countries: Country[]) => Promise<void>;
}) {
  const [countries, setCountries] = useState<Country[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open || !product) return;
    setCountries((product.countries || []).map(country => ({ ...country })));
  }, [open, product]);

  if (!open || !product) return null;

  function updateCountry(id: string, patch: Partial<Country>) {
    setCountries(prev => prev.map(country => country.id === id ? { ...country, ...patch } : country));
  }

  function addCountry() {
    const name = 'New Country';
    setCountries(prev => [
      ...prev,
      {
        id: crypto.randomUUID(),
        name,
        reelFarmCode: codeFromName(name),
        concepts: [],
        creatorCount: 0,
        materialCount: 0,
        postCount: 0
      }
    ]);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave(countries.map(country => ({
        ...country,
        name: (country.name || '未命名地区').trim(),
        reelFarmCode: (country.reelFarmCode || codeFromName(country.name)).trim().toUpperCase()
      })));
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="database-modal is-open" onClick={event => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="country-settings-panel" role="dialog" aria-modal="true" aria-labelledby="countrySettingsTitle">
        <header className="database-header">
          <div>
            <h2 id="countrySettingsTitle" className="database-title">国家/地区设置</h2>
            <p className="database-subtitle">添加、删除或修改 {product.name} 下面的国家/地区和 Country Code。</p>
          </div>
          <button className="icon-btn" type="button" onClick={onClose} title="关闭">×</button>
        </header>
        <form className="country-settings-body" onSubmit={submit}>
          <div className="country-settings-list">
            {countries.map(country => (
              <div className="country-settings-row" key={country.id}>
                <label className="settings-field">
                  <span>国家/地区</span>
                  <input className="text-input" value={country.name || ''} onChange={event => updateCountry(country.id, { name: event.target.value })} />
                </label>
                <label className="settings-field">
                  <span>Country Code</span>
                  <input className="text-input" value={country.reelFarmCode || ''} onChange={event => updateCountry(country.id, { reelFarmCode: event.target.value.toUpperCase() })} placeholder="例如 US / GE / FR" />
                </label>
                <button className="btn danger" type="button" onClick={() => setCountries(prev => prev.filter(item => item.id !== country.id))}>删除</button>
              </div>
            ))}
          </div>
          <div className="settings-actions spread">
            <button className="btn ghost" type="button" onClick={addCountry}>添加国家/地区 + Code</button>
            <span>
              <button className="btn ghost" type="button" onClick={onClose}>取消</button>
              <button className="btn primary" type="submit" disabled={saving}>{saving ? '保存中...' : '保存设置'}</button>
            </span>
          </div>
        </form>
      </section>
    </div>
  );
}
