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
    syncingSources,
    error,
    sendResult,
    growthSyncResult,
    sourceSyncResult,
    sendMode,
    setSendMode,
    loadPreview,
    sendReport,
    syncMixpanelGrowth,
    syncReelfarmAndMuseon
  } = useFeishuReport();

  return (
    <section className="feishu-report-page">
      <FeishuReportHero
        reportDate={reportDate}
        setReportDate={setReportDate}
        loading={loading}
        sending={sending}
        syncingGrowth={syncingGrowth}
        syncingSources={syncingSources}
        sendMode={sendMode}
        setSendMode={setSendMode}
        loadPreview={loadPreview}
        sendReport={sendReport}
        syncMixpanelGrowth={syncMixpanelGrowth}
        syncReelfarmAndMuseon={syncReelfarmAndMuseon}
      />

      <FeishuStatusMessages
        error={error}
        payload={payload}
        sendResult={sendResult}
        growthSyncResult={growthSyncResult}
        sourceSyncResult={sourceSyncResult}
      />
      <FeishuReportLayout payload={payload} loading={loading} />
    </section>
  );
}
