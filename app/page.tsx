'use client';

import { AuthGate } from '@/components/AuthGate';
import { CountrySettingsModal } from '@/components/CountrySettingsModal';
import { DashboardRoutes } from '@/components/DashboardRoutes';
import { DatabaseModal } from '@/components/DatabaseModal';
import { ProductSettingsModal } from '@/components/ProductSettingsModal';
import { SideMenu } from '@/components/SideMenu';
import { useDashboardApp } from '@/hooks/useDashboardApp';

export default function DashboardPage() {
  const dashboard = useDashboardApp();

  if (!dashboard.authenticated) return <AuthGate onLogin={dashboard.login} />;

  return (
    <div className="app">
      <div className={`app-layout ${dashboard.sideCollapsed ? 'side-collapsed' : ''}`}>
        <SideMenu
          tool={dashboard.tool}
          setTool={dashboard.setTool}
          collapsed={dashboard.sideCollapsed}
          onToggle={() => dashboard.setSideCollapsed(value => !value)}
        />
        <DashboardRoutes
          tool={dashboard.tool}
          page={dashboard.page}
          products={dashboard.products}
          productKpis={dashboard.productKpis}
          cloneDisplayProducts={dashboard.cloneDisplayProducts}
          cloneProductKpis={dashboard.cloneProductKpis}
          selectedProduct={dashboard.selectedProduct}
          selectedCloneProduct={dashboard.selectedCloneProduct}
          selectedCountry={dashboard.selectedCountry}
          countryKpis={dashboard.countryKpis}
          currentPrefix={dashboard.currentPrefix}
          syncProductId={dashboard.syncProductId}
          syncPrefix={dashboard.syncPrefix}
          days={dashboard.days}
          reelFarmResults={dashboard.reelFarmResults}
          expandedCards={dashboard.expandedCards}
          postLoading={dashboard.postLoading}
          slideIndexes={dashboard.slideIndexes}
          productTags={dashboard.productTags}
          syncStatus={dashboard.syncStatus}
          syncStatusLoading={dashboard.syncStatusLoading}
          publishCheck={dashboard.publishCheck}
          publishCheckRunning={dashboard.publishCheckRunning}
          publishReminderSending={dashboard.publishReminderSending}
          apiKeys={dashboard.apiKeys}
          generatedKey={dashboard.generatedKey}
          setPage={dashboard.setPage}
          setEditingProductId={dashboard.setEditingProductId}
          setCountrySettingsOpen={dashboard.setCountrySettingsOpen}
          selectProduct={dashboard.selectProduct}
          selectCountry={dashboard.selectCountry}
          addProduct={dashboard.addProduct}
          syncProductCountries={dashboard.syncProductCountries}
          syncCloneProductCountries={dashboard.syncCloneProductCountries}
          changeDays={dashboard.changeDays}
          syncCountry={dashboard.syncCountry}
          toggleCard={dashboard.toggleCard}
          pagePosts={dashboard.pagePosts}
          moveSlide={dashboard.moveSlide}
          addCardTag={dashboard.addCardTag}
          removeCardTag={dashboard.removeCardTag}
          loadSyncStatus={dashboard.loadSyncStatus}
          savePublishCheck={dashboard.savePublishCheck}
          runPublishCheckNow={dashboard.runPublishCheckNow}
          sendPublishReminderNow={dashboard.sendPublishReminderNow}
          createKey={dashboard.createKey}
          revokeKey={dashboard.revokeKey}
          copy={dashboard.copy}
        />
      </div>
      <DatabaseModal
        open={dashboard.databaseOpen}
        snapshot={dashboard.snapshot}
        keys={dashboard.apiKeys}
        generatedKey={dashboard.generatedKey}
        onClose={() => dashboard.setDatabaseOpen(false)}
        onRefresh={dashboard.refreshDatabase}
        onCreateKey={dashboard.createKey}
        onRevokeKey={dashboard.revokeKey}
        onCopy={dashboard.copy}
      />
      <ProductSettingsModal
        open={Boolean(dashboard.editingProductId)}
        product={dashboard.editingProduct}
        onClose={() => dashboard.setEditingProductId('')}
        onSave={dashboard.saveProductSettings}
        readLogo={dashboard.readProductLogo}
      />
      <CountrySettingsModal
        open={dashboard.countrySettingsOpen}
        product={dashboard.selectedProduct}
        onClose={() => dashboard.setCountrySettingsOpen(false)}
        onSave={dashboard.saveCountrySettings}
      />
    </div>
  );
}
