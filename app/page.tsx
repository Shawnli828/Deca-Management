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
import { api } from '@/lib/api';
import type { Country, Product } from '@/lib/types';
import { buildCountryAutomationPrefix, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

export default function DashboardPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [tool, setTool] = useState<'growth' | 'businessReport' | 'feishuReport' | 'slideshow' | 'cloneSlideshow' | 'cloudPhones' | 'publishCheck' | 'apiKeys'>('growth');
  const [sideCollapsed, setSideCollapsed] = useState(false);
  const [page, setPage] = useState<'products' | 'product' | 'country'>('products');
  const [status, setStatus] = useState('正在连接数据库...');
  const [statusError, setStatusError] = useState(false);
  const [syncPrefix, setSyncPrefix] = useState('');
  const [syncProductId, setSyncProductId] = useState('');
  const [syncAllRunning, setSyncAllRunning] = useState(false);
  const [syncAllProgress, setSyncAllProgress] = useState('');
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

  function applySyncResult(productId: string, countryId: string, payload: { creator_count?: number; material_count?: number; synced_at?: string }) {
    setProducts(prev => prev.map(product => {
      if (product.id !== productId) return product;
      const countries = (product.countries || []).map(country => (
        country.id === countryId
          ? {
              ...country,
              creatorCount: Number(payload.creator_count) || 0,
              materialCount: Number(payload.material_count) || 0,
              reelFarmSyncedAt: payload.synced_at || country.reelFarmSyncedAt
            }
          : country
      ));
      return {
        ...product,
        countries,
        creatorCount: countries.reduce((sum, country) => sum + (Number(country.creatorCount) || 0), 0),
        materialCount: countries.reduce((sum, country) => sum + (Number(country.materialCount) || 0), 0)
      };
    }));
  }

  function wait(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async function syncCountry() {
    if (!selectedProduct || !selectedCountry) return;
    const prefix = buildCountryAutomationPrefix(selectedProduct, selectedCountry);
    setSyncPrefix(`country:${selectedCountry.id}`);
    try {
      const payload = await api.syncCountry({
        prefix,
        product_id: selectedProduct.id,
        country_id: selectedCountry.id,
        product_code: getProductReelFarmCode(selectedProduct),
        country_code: getCountryReelFarmCode(selectedCountry)
      });
      applySyncResult(selectedProduct.id, selectedCountry.id, payload);
      resetReelFarmState({ includeResults: false });
      await loadAccounts(selectedProduct, selectedCountry, true);
      await loadProductKpis(selectedProduct);
      await loadCountryKpis(selectedProduct, selectedCountry);
      setStatus(`当前区同步完成：${payload.creator_count} 个账号，${payload.material_count} 个素材`);
      setStatusError(false);
    } catch (error: any) {
      setStatus(error?.message || 'ReelFarm 同步失败');
      setStatusError(true);
    } finally {
      setSyncPrefix('');
    }
  }

  async function syncProductCountries(product: Product) {
    const countries = product.countries || [];
    if (!countries.length || syncProductId) return;
    setSyncProductId(product.id);
    resetReelFarmState();
    let failed = 0;
    try {
      for (let index = 0; index < countries.length; index += 1) {
        const country = countries[index];
        setSyncPrefix(`country:${country.id}`);
        setStatus(`同步 ${product.name}：${index + 1}/${countries.length} ${country.name}`);
        setStatusError(false);
        try {
          const payload = await api.syncCountry({
            prefix: buildCountryAutomationPrefix(product, country),
            product_id: product.id,
            country_id: country.id,
            product_code: getProductReelFarmCode(product),
            country_code: getCountryReelFarmCode(country)
          });
          applySyncResult(product.id, country.id, payload);
        } catch (error: any) {
          failed += 1;
          setStatus(`${product.name} · ${country.name} 同步失败：${error?.message || '未知错误'}`);
          setStatusError(true);
        }
        if (index < countries.length - 1) await wait(1400);
      }
      await loadProductKpis(product);
      if (selectedProductId === product.id && page === 'country') {
        await loadCountryKpis(selectedProduct, selectedCountry);
        await loadAccounts(selectedProduct, selectedCountry, true);
      }
      setStatus(failed ? `${product.name} 同步完成：${failed} 个地区失败` : `${product.name} 已同步完成`);
      setStatusError(Boolean(failed));
    } finally {
      setSyncPrefix('');
      setSyncProductId('');
    }
  }

  async function syncCloneProductCountries(product: Product) {
    const countries = product.countries || [];
    if (!countries.length || syncProductId) return;
    setSyncProductId(product.id);
    let failed = 0;
    try {
      for (let index = 0; index < countries.length; index += 1) {
        const country = countries[index];
        setSyncPrefix(`clone:${country.id}`);
        setStatus(`同步 Clone ${product.name}：${index + 1}/${countries.length} ${country.name}`);
        setStatusError(false);
        try {
          await api.syncMuseonCloneCountry({
            product_id: product.id,
            country_id: country.id,
            product_code: getProductReelFarmCode(product),
            country_code: getCountryReelFarmCode(country)
          });
        } catch (error: any) {
          failed += 1;
          setStatus(`Clone ${product.name} · ${country.name} 同步失败：${error?.message || '未知错误'}`);
          setStatusError(true);
        }
        if (index < countries.length - 1) await wait(900);
      }
      await loadCloneProductData(products);
      setStatus(failed ? `Clone ${product.name} 同步完成：${failed} 个地区失败` : `Clone ${product.name} 已同步完成`);
      setStatusError(Boolean(failed));
    } finally {
      setSyncPrefix('');
      setSyncProductId('');
    }
  }

  async function syncAllCountries() {
    if (syncAllRunning) return;
    const jobs = products.flatMap(product => (product.countries || []).map(country => ({ product, country })));
    if (!jobs.length) return;
    setSyncAllRunning(true);
    resetReelFarmState();
    let failed = 0;
    try {
      for (let index = 0; index < jobs.length; index += 1) {
        const { product, country } = jobs[index];
        const progress = `${index + 1}/${jobs.length}`;
        setSyncAllProgress(progress);
        setStatus(`同步全部中：${progress} ${product.name} · ${country.name}`);
        setStatusError(false);
        setSyncPrefix(`country:${country.id}`);
        try {
          const payload = await api.syncCountry({
            prefix: buildCountryAutomationPrefix(product, country),
            product_id: product.id,
            country_id: country.id,
            product_code: getProductReelFarmCode(product),
            country_code: getCountryReelFarmCode(country)
          });
          applySyncResult(product.id, country.id, payload);
        } catch (error: any) {
          failed += 1;
          setStatus(`${product.name} · ${country.name} 同步失败：${error?.message || '未知错误'}`);
          setStatusError(true);
        }
        if (index < jobs.length - 1) await wait(1800);
      }
      setStatus(failed ? `同步全部完成：${failed} 个地区失败，可单独重试` : '同步全部完成');
      setStatusError(Boolean(failed));
      await Promise.all(products.map(product => loadProductKpis(product)));
      if (page === 'country') await loadCountryKpis(selectedProduct, selectedCountry);
      if (page === 'country') {
        await loadAccounts(selectedProduct, selectedCountry, true);
      }
    } finally {
      setSyncPrefix('');
      setSyncAllProgress('');
      setSyncAllRunning(false);
    }
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
