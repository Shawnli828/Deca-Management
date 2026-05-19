'use client';

import type { Product } from '@/lib/types';
import { normalizeProductFolder } from '@/lib/utils';

export function ProductList({
  products,
  onSelect,
  onAddProduct,
  onEditProduct
}: {
  products: Product[];
  onSelect: (product: Product) => void;
  onAddProduct: () => void;
  onEditProduct: (product: Product) => void;
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
        <button className="btn primary" type="button" onClick={onAddProduct}>添加产品</button>
      </div>
      {Object.entries(groups).map(([folder, items]) => (
        <section className="product-folder" key={folder}>
          <h3>{folder}</h3>
          <div className="product-list">
            {items.map(product => (
              <article className="product-card" key={product.id}>
                <button
                  className="product-settings-btn"
                  type="button"
                  onClick={() => onEditProduct(product)}
                  title="产品设置"
                  aria-label={`${product.name || '产品'} 设置`}
                >
                  ⚙
                </button>
                <button className="product-logo product-logo-display" type="button" onClick={() => onSelect(product)} title="打开产品">
                  {product.logo ? <img src={product.logo} alt="" /> : product.name?.slice(0, 1)}
                </button>
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
