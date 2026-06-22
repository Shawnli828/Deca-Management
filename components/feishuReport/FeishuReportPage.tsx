'use client';

import { useFeishuReport } from '@/hooks/useFeishuReport';
import {
  FeishuReportHero
} from './FeishuReportParts';
import {
  FeishuReportLayout,
  FeishuStatusMessages
} from './FeishuReportPanels';

export function FeishuReportPage() {
  const {
    reportDate,
    setReportDate,
    payload,
    loading,
    sending,
    syncingGrowth,
    error,
    sendResult,
    growthSyncResult,
    sendMode,
    setSendMode,
    products,
    loadPreview,
    sendReport,
    syncMixpanelGrowth
  } = useFeishuReport();

  return (
    <section className="feishu-report-page">
      <FeishuReportHero
        reportDate={reportDate}
        setReportDate={setReportDate}
        loading={loading}
        sending={sending}
        syncingGrowth={syncingGrowth}
        sendMode={sendMode}
        setSendMode={setSendMode}
        loadPreview={loadPreview}
        sendReport={sendReport}
        syncMixpanelGrowth={syncMixpanelGrowth}
      />

      <FeishuStatusMessages error={error} sendResult={sendResult} growthSyncResult={growthSyncResult} />
      <FeishuReportLayout payload={payload} loading={loading} reportDate={reportDate} products={products} sendMode={sendMode} />
    </section>
  );
}
