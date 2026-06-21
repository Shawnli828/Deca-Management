'use client';

import { useFeishuReport } from '@/hooks/useFeishuReport';
import {
  FeishuFlowGrid,
  FeishuReportHero
} from './FeishuReportParts';
import {
  FeishuReportLayout,
  FeishuReportSummary,
  FeishuStatusMessages
} from './FeishuReportPanels';

export function FeishuReportPage() {
  const {
    reportDate,
    setReportDate,
    payload,
    loading,
    sending,
    error,
    sendResult,
    sendMode,
    setSendMode,
    totals,
    products,
    downloadRate,
    loadPreview,
    sendReport
  } = useFeishuReport();

  return (
    <section className="feishu-report-page">
      <FeishuReportHero
        reportDate={reportDate}
        setReportDate={setReportDate}
        loading={loading}
        sending={sending}
        sendMode={sendMode}
        setSendMode={setSendMode}
        loadPreview={loadPreview}
        sendReport={sendReport}
      />

      <FeishuStatusMessages error={error} sendResult={sendResult} />
      <FeishuFlowGrid sendMode={sendMode} />
      <FeishuReportSummary totals={totals} downloadRate={downloadRate} />
      <FeishuReportLayout payload={payload} loading={loading} reportDate={reportDate} products={products} sendMode={sendMode} />
    </section>
  );
}
