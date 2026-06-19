'use client';

import type { Product } from '@/lib/types';
import { formatNumber } from '@/lib/utils';
import { useCloudPhoneMap } from '@/hooks/useCloudPhoneMap';
import {
  CloudCountryStack,
  CloudPhoneDetailLayer,
  CloudProductRail,
  CloudSeatToolbar
} from './CloudPhoneMapParts';

export function CloudPhoneMap({ products }: { products: Product[] }) {
  const {
    cloudProducts,
    countrySections,
    geeLarkError,
    geeLarkLoading,
    liveLabel,
    selectedPhoneTitle,
    selectedProduct,
    selectedSlot,
    selectedSlotId,
    setSelectedProductId,
    setSelectedSlotId,
    totals
  } = useCloudPhoneMap(products);

  return (
    <section className="cloud-phone-page">
      <header className="cloud-phone-hero">
        <div>
          <p className="dashboard-kicker">GeeLark Cloud Phone</p>
          <h1>云手机分布图</h1>
          <p>按「产品 → 国家 → IP 分组 → 云手机」查看 GeeLark 资产。真实命名里 US-DB、DB-US 这类顺序都会识别到对应产品和地区。</p>
        </div>
        <div className="cloud-phone-status">
          <span>{geeLarkLoading ? '正在读取 GeeLark' : liveLabel}</span>
          <strong>{formatNumber(totals.phones)}</strong>
          <small>台云手机</small>
        </div>
      </header>

      {geeLarkError ? (
        <div className="cloud-inline-warning">
          GeeLark 接口暂未返回真实数据：{geeLarkError}。当前页面先显示产品结构预览；配置 GEELARK_API_TOKEN 后会自动读取所有产品和地区。
        </div>
      ) : null}

      <div className="cloud-phone-layout">
        <CloudProductRail
          products={cloudProducts}
          selectedProductId={selectedProduct?.id}
          onSelectProduct={productId => {
            setSelectedProductId(productId);
            setSelectedSlotId('');
          }}
        />

        <section className="cloud-seat-map">
          <CloudSeatToolbar
            selectedProduct={selectedProduct}
            selectedPhoneTitle={selectedPhoneTitle}
            selectedSlot={selectedSlot}
            totals={totals}
          />
          <CloudCountryStack
            countrySections={countrySections}
            selectedProductCode={selectedProduct?.code}
            selectedSlotId={selectedSlotId}
            onSelectSlot={setSelectedSlotId}
          />
        </section>
      </div>

      <CloudPhoneDetailLayer
        selectedPhoneTitle={selectedPhoneTitle}
        selectedSlot={selectedSlot}
        onClose={() => setSelectedSlotId('')}
      />
    </section>
  );
}
