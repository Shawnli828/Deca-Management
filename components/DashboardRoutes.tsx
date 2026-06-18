'use client';

import { ApiKeyPage } from '@/components/ApiKeyPage';
import { BusinessMaterialReport } from '@/components/BusinessMaterialReport';
import { CloudPhoneMap } from '@/components/CloudPhoneMap';
import { CountryList } from '@/components/CountryList';
import { CountryWorkspace } from '@/components/CountryWorkspace';
import { FeishuReportPage } from '@/components/FeishuReportPage';
import { GrowthDashboard } from '@/components/GrowthDashboard';
import { ProductList } from '@/components/ProductList';
import { PublishCheckBoard } from '@/components/PublishCheckBoard';
import type {
  Country,
  ExternalApiKey,
  Product,
  ProductKpis,
  PublishCheckState,
  ReelFarmCard,
  ReelFarmResult
} from '@/lib/types';
import { getProductReelFarmCode } from '@/lib/utils';

export type DashboardTool =
  | 'growth'
  | 'businessReport'
  | 'feishuReport'
  | 'slideshow'
  | 'cloneSlideshow'
  | 'cloudPhones'
  | 'publishCheck'
  | 'apiKeys';

export type DashboardPageState = 'products' | 'product' | 'country';

type DashboardRoutesProps = {
  tool: DashboardTool;
  page: DashboardPageState;
  products: Product[];
  productKpis: Record<string, ProductKpis | null>;
  cloneDisplayProducts: Product[];
  cloneProductKpis: Record<string, ProductKpis | null>;
  selectedProduct: Product | null;
  selectedCloneProduct: Product | null;
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
  publishCheck: PublishCheckState | null;
  publishCheckRunning: boolean;
  publishReminderSending: boolean;
  apiKeys: ExternalApiKey[];
  generatedKey: string;
  setPage: (page: DashboardPageState) => void;
  setEditingProductId: (id: string) => void;
  setCountrySettingsOpen: (open: boolean) => void;
  selectProduct: (product: Product) => void;
  selectCountry: (country: Country) => void;
  addProduct: () => void | Promise<void>;
  syncProductCountries: (product: Product) => void | Promise<void>;
  syncCloneProductCountries: (product: Product) => void | Promise<void>;
  changeDays: (days: number) => void;
  syncCountry: () => void | Promise<void>;
  toggleCard: (key: string) => void;
  pagePosts: (key: string, direction: number) => void;
  moveSlide: (videoId: string, direction: number, total: number) => void;
  addCardTag: (card: ReelFarmCard, tag: string) => void | Promise<void>;
  removeCardTag: (card: ReelFarmCard, tag: string) => void | Promise<void>;
  savePublishCheck: (state: PublishCheckState) => Promise<void>;
  runPublishCheckNow: () => Promise<void>;
  sendPublishReminderNow: () => Promise<void>;
  createKey: (name: string) => Promise<void>;
  revokeKey: (id: string) => void;
  copy: (value: string) => void;
};

export function DashboardRoutes({
  tool,
  page,
  products,
  productKpis,
  cloneDisplayProducts,
  cloneProductKpis,
  selectedProduct,
  selectedCloneProduct,
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
  publishCheck,
  publishCheckRunning,
  publishReminderSending,
  apiKeys,
  generatedKey,
  setPage,
  setEditingProductId,
  setCountrySettingsOpen,
  selectProduct,
  selectCountry,
  addProduct,
  syncProductCountries,
  syncCloneProductCountries,
  changeDays,
  syncCountry,
  toggleCard,
  pagePosts,
  moveSlide,
  addCardTag,
  removeCardTag,
  savePublishCheck,
  runPublishCheckNow,
  sendPublishReminderNow,
  createKey,
  revokeKey,
  copy
}: DashboardRoutesProps) {
  return (
    <main className="shell">
      <section className={`tool-page ${tool === 'growth' ? 'active' : ''}`}>
        <GrowthDashboard products={products} />
      </section>
      <section className={`tool-page ${tool === 'businessReport' ? 'active' : ''}`}>
        <BusinessMaterialReport products={products} />
      </section>
      <section className={`tool-page ${tool === 'feishuReport' ? 'active' : ''}`}>
        <FeishuReportPage />
      </section>
      <section className={`tool-page ${tool === 'slideshow' ? 'active' : ''}`}>
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
      </section>
      <section className={`tool-page ${tool === 'cloneSlideshow' ? 'active' : ''}`}>
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
      </section>
      <section className={`tool-page ${tool === 'cloudPhones' ? 'active' : ''}`}>
        <CloudPhoneMap products={products} />
      </section>
      <section className={`tool-page ${tool === 'apiKeys' ? 'active' : ''}`}>
        <ApiKeyPage
          keys={apiKeys}
          generatedKey={generatedKey}
          onCreateKey={createKey}
          onRevokeKey={revokeKey}
          onCopy={copy}
        />
      </section>
      <section className={`tool-page ${tool === 'publishCheck' ? 'active' : ''}`}>
        <header className="topbar">
          <div>
            <h1>发布检查</h1>
            <p className="subtitle">按负责人检查产品国家下的 TikTok account 今日是否发布。</p>
          </div>
          <div className="top-actions"><span className="status-pill">北京时间 23:00 自动检查</span></div>
        </header>
        <PublishCheckBoard
          products={products}
          state={publishCheck}
          running={publishCheckRunning}
          sendingReminder={publishReminderSending}
          onSave={savePublishCheck}
          onRun={runPublishCheckNow}
          onSendReminder={sendPublishReminderNow}
        />
      </section>
    </main>
  );
}
