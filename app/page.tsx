'use client';

import { useEffect, useMemo, useState } from 'react';
import { AuthGate } from '@/components/AuthGate';
import { CountryList } from '@/components/CountryList';
import { CountrySettingsModal } from '@/components/CountrySettingsModal';
import { CountryWorkspace } from '@/components/CountryWorkspace';
import { DatabaseModal } from '@/components/DatabaseModal';
import { MetricsBar } from '@/components/MetricsBar';
import { ProductList } from '@/components/ProductList';
import { ProductSettingsModal } from '@/components/ProductSettingsModal';
import { PublishCheckBoard } from '@/components/PublishCheckBoard';
import { RoasterBoard } from '@/components/RoasterBoard';
import { SideMenu } from '@/components/SideMenu';
import { accountSummaryToCard, api, mergePostRowsIntoCard } from '@/lib/api';
import type { Country, DatabaseSnapshot, ExternalApiKey, Product, ProductKpis, PublishCheckState, ReelFarmResult, RoasterState } from '@/lib/types';
import { buildCountryAutomationPrefix, cardStateKey, codeFromName, getCountryReelFarmCode, getProductReelFarmCode } from '@/lib/utils';

const defaultRoaster: RoasterState = {
  people: [
    { id: 'han', name: 'han' },
    { id: 'li-zihan', name: '李梓瞻' },
    { id: 'ding-lifeng', name: '丁立峰' },
    { id: 'wang-hengjia', name: '王恒加' },
    { id: 'jj', name: 'JJ' },
    { id: 'doris', name: 'Doris' },
    { id: 'mina', name: 'Mina' }
  ],
  assignments: {}
};

export default function DashboardPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [tool, setTool] = useState<'slideshow' | 'roaster' | 'publishCheck'>('slideshow');
  const [page, setPage] = useState<'products' | 'product' | 'country'>('products');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedCountryId, setSelectedCountryId] = useState('');
  const [status, setStatus] = useState('正在连接数据库...');
  const [statusError, setStatusError] = useState(false);
  const [days, setDays] = useState(30);
  const [reelFarmResults, setReelFarmResults] = useState<Record<string, ReelFarmResult>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [postLoading, setPostLoading] = useState<Record<string, boolean>>({});
  const [postCache, setPostCache] = useState<Record<string, { data: any[]; pagination: { limit: number; offset: number; has_more: boolean; total?: number } }>>({});
  const [slideIndexes, setSlideIndexes] = useState<Record<string, number>>({});
  const [syncPrefix, setSyncPrefix] = useState('');
  const [syncAllRunning, setSyncAllRunning] = useState(false);
  const [syncAllProgress, setSyncAllProgress] = useState('');
  const [roaster, setRoaster] = useState<RoasterState>(defaultRoaster);
  const [publishCheck, setPublishCheck] = useState<PublishCheckState>({ assignments: [], last_result: null });
  const [publishCheckRunning, setPublishCheckRunning] = useState(false);
  const [publishReminderSending, setPublishReminderSending] = useState(false);
  const [databaseOpen, setDatabaseOpen] = useState(false);
  const [editingProductId, setEditingProductId] = useState('');
  const [countrySettingsOpen, setCountrySettingsOpen] = useState(false);
  const [snapshot, setSnapshot] = useState<DatabaseSnapshot | null>(null);
  const [apiKeys, setApiKeys] = useState<ExternalApiKey[]>([]);
  const [generatedKey, setGeneratedKey] = useState('');
  const [productKpis, setProductKpis] = useState<Record<string, ProductKpis | null>>({});

  const selectedProduct = useMemo(() => products.find(product => product.id === selectedProductId) || products[0] || null, [products, selectedProductId]);
  const selectedCountry = useMemo(() => selectedProduct?.countries?.find(country => country.id === selectedCountryId) || selectedProduct?.countries?.[0] || null, [selectedProduct, selectedCountryId]);
  const editingProduct = useMemo(() => products.find(product => product.id === editingProductId) || null, [products, editingProductId]);
  const currentPrefix = selectedProduct && selectedCountry ? buildCountryAutomationPrefix(selectedProduct, selectedCountry) : '';

  useEffect(() => {
    document.title = 'DECAGROWTH中台';
    api.logout().catch(() => {});
  }, []);

  async function loadApp() {
    const payload = await api.data();
    const data = Array.isArray(payload.data) ? payload.data : [];
    setProducts(data);
    setSelectedProductId(data[0]?.id || '');
    setSelectedCountryId(data[0]?.countries?.[0]?.id || '');
    setStatus('已连接数据库');
    setStatusError(false);
    try {
      setRoaster(await api.roaster());
    } catch {
      setRoaster(defaultRoaster);
    }
    try {
      const publishPayload = await api.publishCheck();
      setPublishCheck(publishPayload.state || { assignments: [], last_result: null });
    } catch {
      setPublishCheck({ assignments: [], last_result: null });
    }
  }

  async function login(username: string, password: string) {
    await api.login(username, password);
    setAuthenticated(true);
    await loadApp();
  }

  async function saveProducts(nextProducts: Product[]) {
    setProducts(nextProducts);
    try {
      const payload = await api.saveData(nextProducts);
      setProducts(payload.data || nextProducts);
      setStatus('已保存到数据库');
      setStatusError(false);
      return true;
    } catch {
      setStatus('保存失败');
      setStatusError(true);
      return false;
    }
  }

  function readFileAsDataUrl(file: File) {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error || new Error('Logo 读取失败'));
      reader.readAsDataURL(file);
    });
  }

  async function readProductLogo(file: File) {
    if (!file.type.startsWith('image/')) {
      setStatus('请选择图片文件');
      setStatusError(true);
      throw new Error('请选择图片文件');
    }

    return readFileAsDataUrl(file);
  }

  async function addProduct() {
    const name = window.prompt('输入产品名称');
    if (!name?.trim()) return;
    const newProduct: Product = {
      id: crypto.randomUUID(),
      name: name.trim(),
      folder: '甲方',
      owner_type: '甲方',
      logo: '',
      reelFarmCode: codeFromName(name),
      countries: [],
      creatorCount: 0,
      materialCount: 0,
      postCount: 0
    };
    const saved = await saveProducts([...products, newProduct]);
    if (saved) {
      setSelectedProductId(newProduct.id);
      setEditingProductId(newProduct.id);
      setPage('products');
      setStatus(`${newProduct.name} 已添加`);
      setStatusError(false);
    }
  }

  async function saveProductSettings(value: { name: string; folder: string; reelFarmCode: string; logo?: string }) {
    const product = editingProduct;
    if (!product) return;
    const nextProducts = products.map(item => (
      item.id === product.id
        ? {
            ...item,
            name: value.name,
            folder: value.folder,
            owner_type: value.folder,
            reelFarmCode: value.reelFarmCode || item.reelFarmCode || codeFromName(value.name),
            logo: value.logo || ''
          }
        : item
    ));
    const saved = await saveProducts(nextProducts);
    if (saved) {
      setStatus(`${value.name} 设置已保存`);
      setStatusError(false);
    }
  }

  async function saveCountrySettings(countries: Country[]) {
    const product = selectedProduct;
    if (!product) return;
    const nextProducts = products.map(item => (
      item.id === product.id
        ? { ...item, countries }
        : item
    ));
    const saved = await saveProducts(nextProducts);
    if (saved) {
      const stillSelected = countries.some(country => country.id === selectedCountryId);
      setSelectedCountryId(stillSelected ? selectedCountryId : (countries[0]?.id || ''));
      setReelFarmResults({});
      setPostCache({});
      setExpandedCards({});
      setSlideIndexes({});
      setStatus(`${product.name} 国家/地区设置已保存`);
      setStatusError(false);
    }
  }

  async function loadAccounts(product = selectedProduct, country = selectedCountry, force = false, daysOverride = days) {
    if (!product || !country) return;
    const prefix = buildCountryAutomationPrefix(product, country);
    if (!force && reelFarmResults[prefix]) return;

    setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], loading: true } }));
    try {
      const payload = await api.accounts(getProductReelFarmCode(product), getCountryReelFarmCode(country), daysOverride);
      const cards = (payload.data || []).map(accountSummaryToCard);
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: cards.length, cards } }));
    } catch (error: any) {
      setReelFarmResults(prev => ({ ...prev, [prefix]: { prefix, count: 0, cards: [], error: error?.message || '账号数据加载失败' } }));
    }
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

  function selectProduct(product: Product) {
    setSelectedProductId(product.id);
    setSelectedCountryId(product.countries?.[0]?.id || '');
    setPage('product');
    loadProductKpis(product);
  }

  function selectCountry(country: Country) {
    setSelectedCountryId(country.id);
    setPage('country');
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
      setStatus(`当前区同步完成：${payload.creator_count} 个账号，${payload.material_count} 个素材`);
      setStatusError(false);
    } catch (error: any) {
      setStatus(error?.message || 'ReelFarm 同步失败');
      setStatusError(true);
    } finally {
      setSyncPrefix('');
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
      if (page === 'country') {
        await loadAccounts(selectedProduct, selectedCountry, true);
      }
    } finally {
      setSyncPrefix('');
      setSyncAllProgress('');
      setSyncAllRunning(false);
    }
  }

  async function saveRoaster(next: RoasterState) {
    setRoaster(next);
    try {
      const payload = await api.saveRoaster(next);
      setRoaster(payload.state);
      setStatus('Roaster 已保存');
      setStatusError(false);
    } catch {
      setStatus('Roaster 保存失败');
      setStatusError(true);
    }
  }

  async function savePublishCheck(next: PublishCheckState) {
    setPublishCheck(next);
    try {
      const payload = await api.savePublishCheck(next);
      setPublishCheck(payload.state);
      setStatus('发布检查配置已保存');
      setStatusError(false);
    } catch {
      setStatus('发布检查配置保存失败');
      setStatusError(true);
    }
  }

  async function runPublishCheckNow() {
    setPublishCheckRunning(true);
    try {
      const result = await api.runPublishCheck();
      setPublishCheck(prev => ({ ...prev, last_result: result }));
      setStatus(`发布检查完成：${result.totals?.missing_accounts || 0} 个账号未发布`);
      setStatusError(false);
    } catch (error: any) {
      setStatus(error?.message || '发布检查失败');
      setStatusError(true);
    } finally {
      setPublishCheckRunning(false);
    }
  }

  async function sendPublishReminderNow() {
    setPublishReminderSending(true);
    try {
      const result = await api.sendPublishCheckReminder();
      setStatus(`飞书提醒已发送：${result.missing_accounts || 0} 个账号未发布`);
      setStatusError(false);
    } catch (error: any) {
      setStatus(error?.message || '飞书提醒发送失败');
      setStatusError(true);
    } finally {
      setPublishReminderSending(false);
    }
  }

  async function openDatabase() {
    setDatabaseOpen(true);
    setGeneratedKey('');
    const payload = await api.apiKeys();
    setApiKeys(payload.keys || []);
  }

  async function refreshDatabase() {
    setSnapshot(await api.database());
  }

  async function createKey(name: string) {
    const payload = await api.createApiKey(name);
    setGeneratedKey(payload.key);
    const keys = await api.apiKeys();
    setApiKeys(keys.keys || []);
  }

  async function revokeKey(id: string) {
    if (!confirm('确定要停用这个 API Key 吗？停用后外部 AI 将无法继续使用它。')) return;
    await api.revokeApiKey(id);
    const keys = await api.apiKeys();
    setApiKeys(keys.keys || []);
  }

  async function copy(value: string) {
    await navigator.clipboard.writeText(value);
    setStatus('已复制');
    setStatusError(false);
  }

  if (!authenticated) return <AuthGate onLogin={login} />;

  return (
    <div className="app">
      <div className="app-layout">
        <SideMenu tool={tool} setTool={setTool} />
        <main className="shell">
          <section className={`tool-page ${tool === 'slideshow' ? 'active' : ''}`}>
            <header className="topbar">
              <div>
                <h1><span className="brand-mark">DECAGROWTH<span className="brand-dot">.</span></span><span className="brand-cn">中台</span></h1>
                <p className="subtitle">Slide Show (Reel Farm) · 按「产品 → 国家/地区 → 创意」逐层管理，适合大量产品和市场内容。</p>
              </div>
              <div className="top-actions">
                <span className={`status-pill ${statusError ? 'error' : ''}`}>{status}</span>
                <button className="btn ghost" type="button" onClick={syncAllCountries} disabled={syncAllRunning || !products.length}>
                  {syncAllRunning ? `同步全部 ${syncAllProgress}` : '同步全部'}
                </button>
                <button className="btn ghost" type="button" onClick={openDatabase}>打开数据库</button>
                <button className="btn ghost" type="button" onClick={async () => {
                  const payload = await api.reset();
                  setProducts(payload.data || []);
                  setPage('products');
                }}>恢复示例</button>
              </div>
            </header>
            <MetricsBar products={products} />
            <section className="page-shell">
              {page === 'products' ? <ProductList products={products} onSelect={selectProduct} onAddProduct={addProduct} onEditProduct={product => setEditingProductId(product.id)} /> : null}
              {page === 'product' && selectedProduct ? <CountryList product={selectedProduct} kpis={productKpis[selectedProduct.id]} onBack={() => setPage('products')} onSelect={selectCountry} onOpenSettings={() => setCountrySettingsOpen(true)} /> : null}
              {page === 'country' && selectedProduct && selectedCountry ? (
                <CountryWorkspace
                  product={selectedProduct}
                  country={selectedCountry}
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
                />
              ) : null}
            </section>
          </section>
          <section className={`tool-page ${tool === 'roaster' ? 'active' : ''}`}>
            <header className="topbar">
              <div>
                <h1>Roaster</h1>
                <p className="subtitle">按 App 管理负责人和执行人，把人员拖进对应职责格子即可。</p>
              </div>
              <div className="top-actions"><span className="status-pill">团队排班</span></div>
            </header>
            <RoasterBoard products={products} state={roaster} onChange={saveRoaster} />
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
              roaster={roaster}
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
