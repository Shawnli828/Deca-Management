'use client';

import { useEffect, useRef, useState } from 'react';
import { AuthGate } from '@/components/AuthGate';
import { CountrySettingsModal } from '@/components/CountrySettingsModal';
import type { DashboardPageState, DashboardTool } from '@/components/DashboardRoutes';
import { DashboardRoutes } from '@/components/DashboardRoutes';
import { DatabaseModal } from '@/components/DatabaseModal';
import { ProductSettingsModal } from '@/components/ProductSettingsModal';
import { SideMenu } from '@/components/SideMenu';
import { useDatabaseAccess } from '@/hooks/useDatabaseAccess';
import { useProductCatalog } from '@/hooks/useProductCatalog';
import { useProductMetrics } from '@/hooks/useProductMetrics';
import { usePublishCheck } from '@/hooks/usePublishCheck';
import { useReelFarmDashboard } from '@/hooks/useReelFarmDashboard';
import { useReelFarmSync } from '@/hooks/useReelFarmSync';
import { api } from '@/lib/api';
import type { Country, Product } from '@/lib/types';
import { buildCountryAutomationPrefix } from '@/lib/utils';

export default function DashboardPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [tool, setTool] = useState<DashboardTool>('growth');
  const [sideCollapsed, setSideCollapsed] = useState(false);
  const [page, setPage] = useState<DashboardPageState>('products');
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
        <DashboardRoutes
          tool={tool}
          page={page}
          products={products}
          productKpis={productKpis}
          cloneDisplayProducts={cloneDisplayProducts}
          cloneProductKpis={cloneProductKpis}
          selectedProduct={selectedProduct}
          selectedCloneProduct={selectedCloneProduct}
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
          publishCheck={publishCheck}
          publishCheckRunning={publishCheckRunning}
          publishReminderSending={publishReminderSending}
          apiKeys={apiKeys}
          generatedKey={generatedKey}
          setPage={setPage}
          setEditingProductId={setEditingProductId}
          setCountrySettingsOpen={setCountrySettingsOpen}
          selectProduct={selectProduct}
          selectCountry={selectCountry}
          addProduct={addProduct}
          syncProductCountries={syncProductCountries}
          syncCloneProductCountries={syncCloneProductCountries}
          changeDays={changeDays}
          syncCountry={syncCountry}
          toggleCard={toggleCard}
          pagePosts={pagePosts}
          moveSlide={moveSlide}
          addCardTag={addCardTag}
          removeCardTag={removeCardTag}
          savePublishCheck={savePublishCheck}
          runPublishCheckNow={runPublishCheckNow}
          sendPublishReminderNow={sendPublishReminderNow}
          createKey={createKey}
          revokeKey={revokeKey}
          copy={copy}
        />
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
