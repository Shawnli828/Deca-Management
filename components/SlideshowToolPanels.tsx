'use client';

import { CountryList } from '@/components/CountryList';
import { CountryWorkspace } from '@/components/CountryWorkspace';
import { ProductList } from '@/components/ProductList';
import type {
  Country,
  Product,
  ProductKpis,
  ReelFarmCard,
  ReelFarmResult
} from '@/lib/types';
import { getProductReelFarmCode } from '@/lib/utils';
import type { DashboardPageState } from './DashboardRoutes';

type SlideshowToolPanelProps = {
  page: DashboardPageState;
  products: Product[];
  productKpis: Record<string, ProductKpis | null>;
  selectedProduct: Product | null;
  selectedCountry: Country | null;
  countryKpis: Record<string, ProductKpis | null>;
  currentPrefix: string;
  syncProductId: string;
  syncPrefix: string;
  days: number;
  reelFarmResults: Record<string, ReelFarmResult>;
  expandedCards: Record<string, boolean>;
  postLoading: Record<string, boolean>;
  slideIndexes: Record<string, number>;
  productTags: Record<string, string[]>;
  setPage: (page: DashboardPageState) => void;
  setEditingProductId: (id: string) => void;
  setCountrySettingsOpen: (open: boolean) => void;
  selectProduct: (product: Product) => void;
  selectCountry: (country: Country) => void;
  addProduct: () => void | Promise<void>;
  syncProductCountries: (product: Product) => void | Promise<void>;
  changeDays: (days: number) => void;
  syncCountry: () => void | Promise<void>;
  toggleCard: (key: string) => void;
  pagePosts: (key: string, direction: number) => void;
  moveSlide: (videoId: string, direction: number, total: number) => void;
  addCardTag: (card: ReelFarmCard, tag: string) => void | Promise<void>;
  removeCardTag: (card: ReelFarmCard, tag: string) => void | Promise<void>;
};

type CloneSlideshowToolPanelProps = {
  page: DashboardPageState;
  cloneDisplayProducts: Product[];
  cloneProductKpis: Record<string, ProductKpis | null>;
  selectedProduct: Product | null;
  selectedCloneProduct: Product | null;
  syncProductId: string;
  setPage: (page: DashboardPageState) => void;
  setEditingProductId: (id: string) => void;
  setCountrySettingsOpen: (open: boolean) => void;
  selectProduct: (product: Product) => void;
  selectCountry: (country: Country) => void;
  addProduct: () => void | Promise<void>;
  syncCloneProductCountries: (product: Product) => void | Promise<void>;
};

export function SlideshowToolPanel({
  page,
  products,
  productKpis,
  selectedProduct,
  selectedCountry,
  countryKpis,
  currentPrefix,
  syncProductId,
  syncPrefix,
  days,
  reelFarmResults,
  expandedCards,
  postLoading,
  slideIndexes,
  productTags,
  setPage,
  setEditingProductId,
  setCountrySettingsOpen,
  selectProduct,
  selectCountry,
  addProduct,
  syncProductCountries,
  changeDays,
  syncCountry,
  toggleCard,
  pagePosts,
  moveSlide,
  addCardTag,
  removeCardTag
}: SlideshowToolPanelProps) {
  return (
    <section className="page-shell slideshow-shell">
      {page === 'products' ? (
        <ProductList
          products={products}
          productKpis={productKpis}
          onSelect={selectProduct}
          onAddProduct={addProduct}
          onEditProduct={product => setEditingProductId(product.id)}
        />
      ) : null}
      {page === 'product' && selectedProduct ? (
        <CountryList
          product={selectedProduct}
          kpis={productKpis[selectedProduct.id]}
          syncing={syncProductId === selectedProduct.id}
          onBack={() => setPage('products')}
          onSelect={selectCountry}
          onOpenSettings={() => setCountrySettingsOpen(true)}
          onSyncProduct={syncProductCountries}
        />
      ) : null}
      {page === 'country' && selectedProduct && selectedCountry ? (
        <CountryWorkspace
          product={selectedProduct}
          country={selectedCountry}
          kpis={countryKpis[`${selectedProduct.id}:${selectedCountry.id}`]}
          result={reelFarmResults[currentPrefix]}
          days={days}
          loadingPrefix={syncPrefix}
          expandedCards={expandedCards}
          postLoading={postLoading}
          slideIndexes={slideIndexes}
          onBack={() => setPage('product')}
          onDays={changeDays}
          onSync={syncCountry}
          onToggleCard={toggleCard}
          onPage={pagePosts}
          onMoveSlide={moveSlide}
          onAddTag={addCardTag}
          onRemoveTag={removeCardTag}
          productTags={productTags[getProductReelFarmCode(selectedProduct)] || []}
        />
      ) : null}
    </section>
  );
}

export function CloneSlideshowToolPanel({
  page,
  cloneDisplayProducts,
  cloneProductKpis,
  selectedProduct,
  selectedCloneProduct,
  syncProductId,
  setPage,
  setEditingProductId,
  setCountrySettingsOpen,
  selectProduct,
  selectCountry,
  addProduct,
  syncCloneProductCountries
}: CloneSlideshowToolPanelProps) {
  return (
    <section className="page-shell slideshow-shell">
      {page === 'products' ? (
        <ProductList
          products={cloneDisplayProducts}
          productKpis={cloneProductKpis}
          onSelect={selectProduct}
          onAddProduct={addProduct}
          onEditProduct={product => setEditingProductId(product.id)}
        />
      ) : null}
      {page !== 'products' && selectedProduct ? (
        <CountryList
          product={selectedCloneProduct || selectedProduct}
          kpis={cloneProductKpis[selectedProduct.id]}
          dataSource="museon_clone"
          syncing={syncProductId === selectedProduct.id}
          onBack={() => setPage('products')}
          onSelect={selectCountry}
          onOpenSettings={() => setCountrySettingsOpen(true)}
          onSyncProduct={syncCloneProductCountries}
        />
      ) : null}
    </section>
  );
}
