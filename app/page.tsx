'use client';

import { useEffect, useMemo, useState } from 'react';
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
import { usePublishCheck } from '@/hooks/usePublishCheck';
import { accountSummaryToCard, api, mergePostRowsIntoCard } from '@/lib/api';
import type { Country, Product, ProductKpis, ProductRollup, ReelFarmCard, ReelFarmResult } from '@/lib/types';
import { buildCountryAutomationPrefix, cardStateKey, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

export default function DashboardPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [tool, setTool] = useState<'growth' | 'businessReport' | 'feishuReport' | 'slideshow' | 'cloneSlideshow' | 'cloudPhones' | 'publishCheck' | 'apiKeys'>('growth');
  const [sideCollapsed, setSideCollapsed] = useState(false);
  const [page, setPage] = useState<'products' | 'product' | 'country'>('products');
  const [status, setStatus] = useState('正在连接数据库...');
  const [statusError, setStatusError] = useState(false);
  const [days, setDays] = useState(30);
  const [reelFarmResults, setReelFarmResults] = useState<Record<string, ReelFarmResult>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [postLoading, setPostLoading] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, { data: any[]; pagination: { limit: number; offset: number; has_more: boolean; total?: number } }>>({});
  const [slideIndexes, setSlideIndexes] = useState<Record<string, number>>({});
  const [syncPrefix, setSyncPrefix] = useState('');
  const [syncProductId, setSyncProductId] = useState('');
  const [syncAllRunning, setSyncAllRunning] = useState(false);
  const [syncAllProgress, setSyncAllProgress] = useState('');
  const [productKpis, setProductKpis] = useState<Record<string, ProductKpis | null>>({});
  const [cloneProducts, setCloneProducts] = useState<Product[]>([]);
  const [cloneProductKpis, setCloneProductKpis] = useState<Record<string, ProductKpis | null>>({});
  const [countryKpis, setCountryKpis] = useState<Record<string, ProductKpis | null>>({});
  const [productTags, setProductTags] = useState<Record<string, string[]>>({});

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
    onCountrySettingsSaved: () => {
      setReelFarmResults({});
      setPostCache({});
      setExpandedCards({});
      setSlideIndexes({});
    }
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

  const currentPrefix = selectedProduct && selectedCountry ? buildCountryAutomationPrefix(selectedProduct, selectedCountry) : '';
  const cloneDisplayProducts = useMemo(() => (
    cloneProducts.length ? cloneProducts : products.map(product => ({
      ...product,
      creatorCount: 0,
      automationCount: 0,
      materialCount: 0,
      postCount: 0,
      countries: (product.countries || []).map(country => ({
        ...country,
        creatorCount: 0,
        automationCount: 0,
        materialCount: 0,
        postCount: 0,
        reelFarmSyncedAt: ''
      }))
    }))
  ), [cloneProducts, products]);
  const selectedCloneProduct = useMemo(
    () => cloneDisplayProducts.find(product => product.id === selectedProductId) || cloneDisplayProducts[0] || null,
    [cloneDisplayProducts, selectedProductId]
  );

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

  async function loadAccounts(product = selectedProduct, country = selectedCountry, force = false, daysOverride = days) {
    if (!product || !country) return;
    const prefix = buildCountryAutomationPrefix(product, country);
    if (!force && reelFarmResults[prefix]) return;

    setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], loading: true } }));
    try {
      await loadProductTags(product);
      const payload = await api.accounts(getProductReelFarmCode(product), getCountryReelFarmCode(country), daysOverride);
      let cards = (payload.data || []).map(accountSummaryToCard);
      const accountIds = cards.map(getCardAccountId).filter(Boolean);
      if (accountIds.length) {
        const tagPayload = await api.accountTags(accountIds);
        cards = cards.map(card => ({ ...card, tags: tagPayload.tags[getCardAccountId(card)] || [] }));
      }
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: cards.length, cards } }));
    } catch (error: any) {
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], error: error?.message || '账号数据加载失败' } }));
    }
  }

  async function loadProductTags(product = selectedProduct) {
    if (!product) return [];
    const productCode = getProductReelFarmCode(product);
    const payload = await api.productTags(productCode);
    setProductTags(previous => ({ ...previous, [productCode]: payload.tags || [] }));
    return payload.tags || [];
  }

  function getCardAccountId(card: ReelFarmCard) {
    const account = card.account || {};
    return String(account.id || account.account_id || '').trim();
  }

  useEffect(() => {
    if (authenticated && tool === 'apiKeys') {
      loadApiKeys().catch(() => {});
    }
  }, [authenticated, tool]);

  useEffect(() => {
    if (authenticated && selectedProduct) {
      loadProductTags(selectedProduct).catch(() => {});
    }
  }, [authenticated, selectedProductId]);

  async function addCardTag(card: ReelFarmCard, tag: string) {
    const accountId = getCardAccountId(card);
    if (!accountId) return;
    if (!tag?.trim()) return;
    const product = selectedProduct;
    if (product) {
      const productCode = getProductReelFarmCode(product);
      const productTagPayload = await api.createProductTag(productCode, tag.trim());
      setProductTags(previous => ({ ...previous, [productCode]: productTagPayload.tags || [] }));
    }
    const payload = await api.addAccountTag(accountId, tag.trim());
    updateCardTags(accountId, previous => Array.from(new Set([...previous, payload.tag])));
  }

  async function removeCardTag(card: ReelFarmCard, tag: string) {
    const accountId = getCardAccountId(card);
    if (!accountId) return;
    await api.deleteAccountTag(accountId, tag);
    updateCardTags(accountId, previous => previous.filter(item => item !== tag));
  }

  function updateCardTags(accountId: string, updater: (tags: string[]) => string[]) {
    setReelFarmResults(prev => {
      const next = { ...prev };
      for (const [prefix, result] of Object.entries(next)) {
        next[prefix] = {
          ...result,
          cards: result.cards.map(card => getCardAccountId(card) === accountId ? { ...card, tags: updater(card.tags || []) } : card)
        };
      }
      return next;
    });
  }

  useEffect(() => {
    if (authenticated && page === 'country') {
      loadAccounts(selectedProduct, selectedCountry, false);
    }
  }, [authenticated, page, selectedProductId, selectedCountryId]);

  async function loadProductKpis(product = selectedProduct) {
    if (!product) return;
    try {
      const payload = await api.productKpis(getProductReelFarmCode(product));
      setProductKpis(prev => ({ ...prev, [product.id]: payload.data || null }));
    } catch {
      setProductKpis(prev => ({ ...prev, [product.id]: null }));
    }
  }

  function buildProductsFromRollups(sourceProducts: Product[], rollups: ProductRollup[]) {
    const rollupMap = new Map(
      (rollups || []).map(rollup => [String(rollup.product_code || '').toUpperCase(), rollup])
    );

    return sourceProducts.map(product => {
      const productCode = getProductReelFarmCode(product);
      const rollup = rollupMap.get(productCode);
      const countryRollups = new Map(
        (rollup?.countries || []).map(country => [String(country.country_code || '').toUpperCase(), country])
      );
      const countries = (product.countries || []).map(country => {
        const countryRollup = countryRollups.get(getCountryReelFarmCode(country));
        return {
          ...country,
          creatorCount: Number(countryRollup?.creator_count) || 0,
          materialCount: Number(countryRollup?.material_count) || 0,
          postCount: Number(countryRollup?.post_count) || 0,
          reelFarmSyncedAt: countryRollup?.last_synced_at || ''
        };
      });

      return {
        ...product,
        creatorCount: Number(rollup?.creator_count) || 0,
        materialCount: Number(rollup?.material_count) || 0,
        postCount: Number(rollup?.post_count) || 0,
        countries
      };
    });
  }

  async function loadCloneProductData(sourceProducts = products) {
    if (!sourceProducts.length) return;
    try {
      const rollupPayload = await api.productRollups('museon_clone');
      setCloneProducts(buildProductsFromRollups(sourceProducts, rollupPayload.data || []));
      const entries = await Promise.all(sourceProducts.map(async product => {
        try {
          const payload = await api.productKpis(getProductReelFarmCode(product), undefined, 'museon_clone');
          return [product.id, payload.data || null] as const;
        } catch {
          return [product.id, null] as const;
        }
      }));
      setCloneProductKpis(Object.fromEntries(entries));
    } catch (error: any) {
      setCloneProducts(buildProductsFromRollups(sourceProducts, []));
      setCloneProductKpis({});
      setStatus(error?.message || 'Clone Slide Show 数据加载失败');
      setStatusError(true);
    }
  }

  async function loadCountryKpis(product = selectedProduct, country = selectedCountry) {
    if (!product || !country) return;
    const key = `${product.id}:${country.id}`;
    try {
      const payload = await api.productKpis(getProductReelFarmCode(product), getCountryReelFarmCode(country));
      setCountryKpis(prev => ({ ...prev, [key]: payload.data || null }));
    } catch {
      setCountryKpis(prev => ({ ...prev, [key]: null }));
    }
  }

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
    setReelFarmResults({});
    setPostCache({});
    setPostLoading({});
    setExpandedCards({});
    setSlideIndexes({});
  }

  function changeDays(nextDays: number) {
    if (![7, 14, 30].includes(nextDays)) return;
    setDays(nextDays);
    setReelFarmResults({});
    setPostCache({});
    setExpandedCards({});
    setSlideIndexes({});
    setTimeout(() => loadAccounts(selectedProduct, selectedCountry, true, nextDays), 0);
  }

  function findCard(cardKey: string) {
    for (const result of Object.values(reelFarmResults)) {
      const card = result.cards.find(item => cardStateKey(item) === cardKey);
      if (card) return card;
    }
    return null;
  }

  async function loadPosts(cardKey: string, offset = 0) {
    const product = selectedProduct;
    const country = selectedCountry;
    const card = findCard(cardKey);
    if (!product || !country || !card) return;
    const account = card.account || {};
    const accountId = account.id || account.account_id || account.reelfarm_account_id || account.tiktok_account_id || account.username || account.account_username || '';
    const cacheKey = [getProductReelFarmCode(product), getCountryReelFarmCode(country), accountId, days, offset].join('|');
    const cached = postCache[cacheKey];

    function updateCard(data: any[], pagination: { limit: number; offset: number; has_more: boolean; total?: number }) {
      const prefix = buildCountryAutomationPrefix(product, country);
      setReelFarmResults(prev => {
        const result = prev[prefix];
        if (!result) return prev;
        const cards = result.cards.map(item => {
          if (cardStateKey(item) !== cardKey) return item;
          const clone = structuredClone(item);
          mergePostRowsIntoCard(clone, data);
          clone.pagination = pagination;
          return clone;
        });
        return { ...prev, [prefix]: { ...result, cards } };
      });
    }

    if (cached) {
      updateCard(cached.data, cached.pagination);
      return;
    }

    setPostLoading(prev => ({ ...prev, [cardKey]: true }));
    try {
      const payload = await api.accountPosts(getProductReelFarmCode(product), getCountryReelFarmCode(country), String(accountId), days, 4, offset);
      const pagination = payload.pagination || { limit: 4, offset, has_more: false, total: payload.data?.length || 0 };
      setPostCache(prev => ({ ...prev, [cacheKey]: { data: payload.data || [], pagination } }));
      updateCard(payload.data || [], pagination);
    } catch (error: any) {
      setReelFarmResults(prev => {
        const prefix = buildCountryAutomationPrefix(product, country);
        const result = prev[prefix];
        if (!result) return prev;
        const cards = result.cards.map(item => cardStateKey(item) === cardKey ? { ...item, errors: { videos: null, posts: error?.message || 'Posts loading failed.' } } : item);
        return { ...prev, [prefix]: { ...result, cards } };
      });
    } finally {
      setPostLoading(prev => {
        const next = { ...prev };
        delete next[cardKey];
        return next;
      });
    }
  }

  function toggleCard(cardKey: string) {
    setExpandedCards(prev => {
      const next = { ...prev, [cardKey]: !prev[cardKey] };
      if (next[cardKey]) loadPosts(cardKey, 0);
      return next;
    });
  }

  function pagePosts(cardKey: string, direction: number) {
    const card = findCard(cardKey);
    const limit = Number(card?.pagination?.limit) || 4;
    const offset = Number(card?.pagination?.offset) || 0;
    loadPosts(cardKey, Math.max(0, offset + direction * limit));
  }

  function moveSlide(videoId: string, direction: number, total: number) {
    setSlideIndexes(prev => ({ ...prev, [videoId]: ((prev[videoId] || 0) + direction + total) % total }));
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
      setPostCache({});
      setExpandedCards({});
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
    setPostCache({});
    setExpandedCards({});
    setReelFarmResults({});
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
    setPostCache({});
    setExpandedCards({});
    setReelFarmResults({});
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
