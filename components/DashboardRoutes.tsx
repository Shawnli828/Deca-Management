'use client';

import { ApiKeyPage } from '@/components/ApiKeyPage';
import { AutomationCoveragePage } from '@/components/automationCoverage/AutomationCoveragePage';
import { BusinessMaterialReport } from '@/components/BusinessMaterialReport';
import { CloudPhoneMap } from '@/components/cloudPhone/CloudPhoneMap';
import { FeishuReportPage } from '@/components/feishuReport/FeishuReportPage';
import { GrowthDashboard } from '@/components/GrowthDashboard';
import { CloneSlideshowToolPanel, SlideshowToolPanel } from '@/components/SlideshowToolPanels';
import { DashboardToolSection } from '@/components/dashboard/DashboardToolSection';
import type { SyncStatusResponse } from '@/lib/api/types';
import type {
  Country,
  ExternalApiKey,
  Product,
  ProductKpis,
  ReelFarmCard,
  ReelFarmResult
} from '@/lib/types';

export type DashboardTool =
  | 'growth'
  | 'businessReport'
  | 'feishuReport'
  | 'slideshow'
  | 'cloneSlideshow'
  | 'cloudPhones'
  | 'automationCoverage'
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
  syncStatus: SyncStatusResponse | null;
  syncStatusLoading: boolean;
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
  loadSyncStatus: () => void | Promise<unknown>;
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
  syncStatus,
  syncStatusLoading,
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
  loadSyncStatus,
  createKey,
  revokeKey,
  copy
}: DashboardRoutesProps) {
  return (
    <main className="shell">
      <DashboardToolSection active={tool === 'growth'}>
        <GrowthDashboard products={products} />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'businessReport'}>
        <BusinessMaterialReport products={products} />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'feishuReport'}>
        <FeishuReportPage />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'slideshow'}>
        <SlideshowToolPanel
          page={page}
          products={products}
          productKpis={productKpis}
          selectedProduct={selectedProduct}
          selectedCountry={selectedCountry}
          countryKpis={countryKpis}
          currentPrefix={currentPrefix}
          syncProductId={syncProductId}
          syncPrefix={syncPrefix}
          days={days}
          reelFarmResults={reelFarmResults}
          expandedCards={expandedCards}
          postLoading={postLoading}
          slideIndexes={slideIndexes}
          productTags={productTags}
          syncStatus={syncStatus}
          syncStatusLoading={syncStatusLoading}
          setPage={setPage}
          setEditingProductId={setEditingProductId}
          setCountrySettingsOpen={setCountrySettingsOpen}
          selectProduct={selectProduct}
          selectCountry={selectCountry}
          addProduct={addProduct}
          syncProductCountries={syncProductCountries}
          changeDays={changeDays}
          syncCountry={syncCountry}
          toggleCard={toggleCard}
          pagePosts={pagePosts}
          moveSlide={moveSlide}
          addCardTag={addCardTag}
          removeCardTag={removeCardTag}
          loadSyncStatus={loadSyncStatus}
        />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'cloneSlideshow'}>
        <CloneSlideshowToolPanel
          page={page}
          cloneDisplayProducts={cloneDisplayProducts}
          cloneProductKpis={cloneProductKpis}
          selectedProduct={selectedProduct}
          selectedCloneProduct={selectedCloneProduct}
          syncProductId={syncProductId}
          syncStatus={syncStatus}
          syncStatusLoading={syncStatusLoading}
          setPage={setPage}
          setEditingProductId={setEditingProductId}
          setCountrySettingsOpen={setCountrySettingsOpen}
          selectProduct={selectProduct}
          selectCountry={selectCountry}
          addProduct={addProduct}
          syncCloneProductCountries={syncCloneProductCountries}
          loadSyncStatus={loadSyncStatus}
        />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'cloudPhones'}>
        <CloudPhoneMap products={products} />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'automationCoverage'}>
        <AutomationCoveragePage active={tool === 'automationCoverage'} />
      </DashboardToolSection>
      <DashboardToolSection active={tool === 'apiKeys'}>
        <ApiKeyPage
          keys={apiKeys}
          generatedKey={generatedKey}
          onCreateKey={createKey}
          onRevokeKey={revokeKey}
          onCopy={copy}
        />
      </DashboardToolSection>
    </main>
  );
}
