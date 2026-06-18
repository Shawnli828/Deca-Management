'use client';

import { useEffect, useRef, useState } from 'react';
import { ApiKeyPage } from '@/components/ApiKeyPage';
import { AuthGate } from '@/components/AuthGate';
import { BusinessMaterialReport } from '@/components/BusinessMaterialReport';
import { CloudPhoneMap } from '@/components/CloudPhoneMap';
import { CountryList } from '@/components/CountryList';
import { CountrySettingsModal } from '@/components/CountrySettingsModal';
import { CountryWorkspace } from '@/components/CountryWorkspace';
import { DatabaseModal } from '@/components/DatabaseModal';
import { FeishuReportPage } from '@/components/FeishuReportPage';
import { GrowthDashboard } from '@/components/GrowthDashboard';
import { ProductList } from '@/components/ProductList';
import { ProductSettingsModal } from '@/components/ProductSettingsModal';
import { PublishCheckBoard } from '@/components/PublishCheckBoard';
import { SideMenu } from '@/components/SideMenu';
import { useDatabaseAccess } from '@/hooks/useDatabaseAccess';
import { useProductCatalog } from '@/hooks/useProductCatalog';
import { useProductMetrics } from '@/hooks/useProductMetrics';
import { usePublishCheck } from '@/hooks/usePublishCheck';
import { useReelFarmDashboard } from '@/hooks/useReelFarmDashboard';
import { useReelFarmSync } from '@/hooks/useReelFarmSync';
import { api } from '@/lib/api';
import type { Country, Product } from '@/lib/types';
import { buildCountryAutomationPrefix, getProductReelFarmCode } from '@/lib/utils';

export default function DashboardPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [tool, setTool] = useState<'growth' | 'businessReport' | 'feishuReport' | 'slideshow' | 'cloneSlideshow' | 'cloudPhones' | 'publishCheck' | 'apiKeys'>('growth');
  const [sideCollapsed, setSideCollapsed] = useState(false);
  const [page, setPage] = useState<'products' | 'product' | 'country'>('products');
  const [status, setStatus] = useState('正在连接数据库...');
  const [statusError, setStatusError] = useState(false);
  const reelFarmResetRef = useRef<(() => void) | null>(null);

  function reportStatus(message: string, isError = false) {
    setStatus(message);
    setStatusError(isError);
  }

  const {
    products,
    setProducts,
    selectedProduct,
    selectedCountry,
    editingProduct,
    selectedProductId,
    selectedCountryId,
    editingProductId,
    countrySettingsOpen,
    setSelectedProductId,
    setSelectedCountryId,
    setEditingProductId,
    setCountrySettingsOpen,
    replaceProducts,
    addProduct,
    readProductLogo,
    saveProductSettings,
    saveCountrySettings
  } = useProductCatalog({
    onStatus: reportStatus,
    onProductAdded: () => setPage('products'),
    onCountrySettingsSaved: () => reelFarmResetRef.current?.()
  });

  const {
    databaseOpen,
    snapshot,
    apiKeys,
    generatedKey,
    setDatabaseOpen,
    loadApiKeys,
    refreshDatabase,
    createKey,
    revokeKey,
    copy
  } = useDatabaseAccess({ onStatus: reportStatus });

  const {
    publishCheck,
    publishCheckRunning,
    publishReminderSending,
    loadPublishCheck,
    savePublishCheck,
    runPublishCheckNow,
    sendPublishReminderNow
  } = usePublishCheck({ onStatus: reportStatus });

  const {
    productKpis,
    cloneDisplayProducts,
    selectedCloneProduct,
    cloneProductKpis,
    countryKpis,
    loadProductKpis,
    loadCloneProductData,
    loadCountryKpis
  } = useProductMetrics({
    products,
    selectedProductId,
    onStatus: reportStatus
  });

  const {
    days,
    reelFarmResults,
    expandedCards,
    postLoading,
    slideIndexes,
    productTags,
    loadAccounts,
    addCardTag,
    removeCardTag,
    changeDays,
    toggleCard,
    pagePosts,
    moveSlide,
    resetReelFarmState
  } = useReelFarmDashboard({
    authenticated,
    page,
    selectedProduct,
    selectedCountry,
    selectedProductId,
    selectedCountryId
  });

  const {
    syncPrefix,
    syncProductId,
    syncAllRunning,
    syncAllProgress,
    syncCountry,
    syncProductCountries,
    syncCloneProductCountries,
    syncAllCountries
  } = useReelFarmSync({
    products,
    selectedProduct,
    selectedCountry,
    selectedProductId,
    page,
    setProducts,
    onStatus: reportStatus,
    resetReelFarmState,
    loadAccounts,
    loadProductKpis,
    loadCountryKpis,
    loadCloneProductData
  });

  useEffect(() => {
    reelFarmResetRef.current = resetReelFarmState;
  }, [resetReelFarmState]);

  const currentPrefix = selectedProduct && selectedCountry ? buildCountryAutomationPrefix(selectedProduct, selectedCountry) : '';

  useEffect(() => {
    document.title = 'DECAGROWTH中台';
    api.logout().catch(() => {});
  }, []);

  async function loadApp() {
    const payload = await api.data();
    const data = Array.isArray(payload.data) ? payload.data : [];
    replaceProducts(data);
    void Promise.all(data.map(product => loadProductKpis(product)));
    reportStatus('已连接数据库');
    await loadPublishCheck();
  }

  async function login(username: string, password: string) {
    await api.login(username, password);
    setAuthenticated(true);
    await loadApp();
  }

  useEffect(() => {
    if (authenticated && tool === 'apiKeys') {
      loadApiKeys().catch(() => {});
    }
  }, [authenticated, tool]);

  function selectProduct(product: Product) {
    setSelectedProductId(product.id);
    setSelectedCountryId(product.countries?.[0]?.id || '');
    setPage('product');
    loadProductKpis(product);
  }

  useEffect(() => {
    if (authenticated && tool === 'cloneSlideshow' && products.length) {
      loadCloneProductData(products);
    }
  }, [authenticated, tool, products]);

  function selectCountry(country: Country) {
    setSelectedCountryId(country.id);
    setPage('country');
    loadCountryKpis(selectedProduct, country);
    resetReelFarmState();
  }

  async function resetDemo() {
    const payload = await api.reset();
    replaceProducts(payload.data || []);
    setPage('products');
  }

  if (!authenticated) return <AuthGate onLogin={login} />;

  return (
    <div className="app">
      <div className={`app-layout ${sideCollapsed ? 'side-collapsed' : ''}`}>
        <SideMenu tool={tool} setTool={setTool} collapsed={sideCollapsed} onToggle={() => setSideCollapsed(value => !value)} />
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
      </div>
      <DatabaseModal
        open={databaseOpen}
        snapshot={snapshot}
        keys={apiKeys}
        generatedKey={generatedKey}
        onClose={() => setDatabaseOpen(false)}
        onRefresh={refreshDatabase}
        onCreateKey={createKey}
        onRevokeKey={revokeKey}
        onCopy={copy}
      />
      <ProductSettingsModal
        open={Boolean(editingProductId)}
        product={editingProduct}
        onClose={() => setEditingProductId('')}
        onSave={saveProductSettings}
        readLogo={readProductLogo}
      />
      <CountrySettingsModal
        open={countrySettingsOpen}
        product={selectedProduct}
        onClose={() => setCountrySettingsOpen(false)}
        onSave={saveCountrySettings}
      />
    </div>
  );
}
