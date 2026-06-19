'use client';

import { useEffect, useRef, useState } from 'react';
import type { DashboardPageState, DashboardTool } from '@/components/DashboardRoutes';
import { useDatabaseAccess } from '@/hooks/useDatabaseAccess';
import { useProductCatalog } from '@/hooks/useProductCatalog';
import { useProductMetrics } from '@/hooks/useProductMetrics';
import { usePublishCheck } from '@/hooks/usePublishCheck';
import { useReelFarmDashboard } from '@/hooks/useReelFarmDashboard';
import { useReelFarmSync } from '@/hooks/useReelFarmSync';
import { api } from '@/lib/api';
import type { Country, Product } from '@/lib/types';
import { buildCountryAutomationPrefix } from '@/lib/utils';

export function useDashboardApp() {
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

  const productCatalog = useProductCatalog({
    onStatus: reportStatus,
    onProductAdded: () => setPage('products'),
    onCountrySettingsSaved: () => reelFarmResetRef.current?.()
  });

  const databaseAccess = useDatabaseAccess({ onStatus: reportStatus });

  const publishCheckState = usePublishCheck({ onStatus: reportStatus });

  const productMetrics = useProductMetrics({
    products: productCatalog.products,
    selectedProductId: productCatalog.selectedProductId,
    onStatus: reportStatus
  });

  const reelFarmDashboard = useReelFarmDashboard({
    authenticated,
    page,
    selectedProduct: productCatalog.selectedProduct,
    selectedCountry: productCatalog.selectedCountry,
    selectedProductId: productCatalog.selectedProductId,
    selectedCountryId: productCatalog.selectedCountryId
  });

  const reelFarmSync = useReelFarmSync({
    products: productCatalog.products,
    selectedProduct: productCatalog.selectedProduct,
    selectedCountry: productCatalog.selectedCountry,
    selectedProductId: productCatalog.selectedProductId,
    page,
    setProducts: productCatalog.setProducts,
    onStatus: reportStatus,
    resetReelFarmState: reelFarmDashboard.resetReelFarmState,
    loadAccounts: reelFarmDashboard.loadAccounts,
    loadProductKpis: productMetrics.loadProductKpis,
    loadCountryKpis: productMetrics.loadCountryKpis,
    loadCloneProductData: productMetrics.loadCloneProductData
  });

  useEffect(() => {
    reelFarmResetRef.current = reelFarmDashboard.resetReelFarmState;
  }, [reelFarmDashboard.resetReelFarmState]);

  const currentPrefix = productCatalog.selectedProduct && productCatalog.selectedCountry
    ? buildCountryAutomationPrefix(productCatalog.selectedProduct, productCatalog.selectedCountry)
    : '';

  useEffect(() => {
    document.title = 'DECAGROWTH中台';
    api.logout().catch(() => {});
  }, []);

  async function loadApp() {
    const payload = await api.data();
    const data = Array.isArray(payload.data) ? payload.data : [];
    productCatalog.replaceProducts(data);
    void Promise.all(data.map(product => productMetrics.loadProductKpis(product)));
    reportStatus('已连接数据库');
    await publishCheckState.loadPublishCheck();
  }

  async function login(username: string, password: string) {
    await api.login(username, password);
    setAuthenticated(true);
    await loadApp();
  }

  useEffect(() => {
    if (authenticated && tool === 'apiKeys') {
      databaseAccess.loadApiKeys().catch(() => {});
    }
  }, [authenticated, tool]);

  function selectProduct(product: Product) {
    productCatalog.setSelectedProductId(product.id);
    productCatalog.setSelectedCountryId(product.countries?.[0]?.id || '');
    setPage('product');
    productMetrics.loadProductKpis(product);
  }

  useEffect(() => {
    if (authenticated && tool === 'cloneSlideshow' && productCatalog.products.length) {
      productMetrics.loadCloneProductData(productCatalog.products);
    }
  }, [authenticated, tool, productCatalog.products]);

  function selectCountry(country: Country) {
    productCatalog.setSelectedCountryId(country.id);
    setPage('country');
    productMetrics.loadCountryKpis(productCatalog.selectedProduct, country);
    reelFarmDashboard.resetReelFarmState();
  }

  async function resetDemo() {
    const payload = await api.reset();
    productCatalog.replaceProducts(payload.data || []);
    setPage('products');
  }

  return {
    authenticated,
    tool,
    setTool,
    sideCollapsed,
    setSideCollapsed,
    page,
    setPage,
    status,
    statusError,
    currentPrefix,
    login,
    selectProduct,
    selectCountry,
    resetDemo,
    ...productCatalog,
    ...databaseAccess,
    ...publishCheckState,
    ...productMetrics,
    ...reelFarmDashboard,
    ...reelFarmSync
  };
}
