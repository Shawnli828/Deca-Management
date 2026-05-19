'use client';

import type { Product } from '@/lib/types';
import { normalizeProductFolder } from '@/lib/utils';

export function ProductList({ products, onSelect }: { products: Product[]; onSelect: (product: Product) => void }) {
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
              <button className="product-card" type="button" key={product.id} onClick={() => onSelect(product)}>
                <span className="product-logo">{product.logo ? <img src={product.logo} alt="" /> : product.name?.slice(0, 1)}</span>
                <span className="product-card-copy">
                  <strong className="product-card-name">{product.name || '未命名产品'}</strong>
                  <span className="product-card-meta">{product.countries?.length || 0} 个国家/地区</span>
                </span>
              </button>
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}
