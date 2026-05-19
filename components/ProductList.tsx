'use client';

import type { Product } from '@/lib/types';
import { normalizeProductFolder } from '@/lib/utils';

export function ProductList({
  products,
  onSelect,
  onLogoChange
}: {
  products: Product[];
  onSelect: (product: Product) => void;
  onLogoChange: (product: Product, file: File) => void;
}) {
  const groups = products.reduce<Record<string, Product[]>>((map, product) => {
    const folder = normalizeProductFolder(product);
    map[folder] = map[folder] || [];
    map[folder].push(product);
    return map;
  }, {});

  return (
    <section className="page active">
      <div className="section-head">
        <div>
          <h2>产品总览</h2>
          <p>先从甲方 / 乙方文件夹选择产品，再继续进入国家和 Format。</p>
        </div>
      </div>
      {Object.entries(groups).map(([folder, items]) => (
        <section className="product-folder" key={folder}>
          <h3>{folder}</h3>
          <div className="product-list">
            {items.map(product => (
              <article className="product-card" key={product.id}>
                <label className="product-logo product-logo-upload" title="点击更换 Logo">
                  {product.logo ? <img src={product.logo} alt="" /> : product.name?.slice(0, 1)}
                  <input
                    className="product-logo-input"
                    type="file"
                    accept="image/*"
                    onChange={event => {
                      const file = event.target.files?.[0];
                      if (file) onLogoChange(product, file);
                      event.target.value = '';
                    }}
                  />
                  <span className="product-logo-action">更换 Logo</span>
                </label>
                <button className="product-card-info" type="button" onClick={() => onSelect(product)}>
                  <span className="product-card-copy">
                    <strong className="product-card-name">{product.name || '未命名产品'}</strong>
                    <span className="product-card-meta">
                      {product.countries?.length || 0} 个国家/地区 · {product.creatorCount || 0} 个账号 · {product.materialCount || 0} 个素材
                    </span>
                  </span>
                </button>
              </article>
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}
