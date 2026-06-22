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
    error,
    sendResult,
    sendMode,
    setSendMode,
    products,
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
      <FeishuReportLayout payload={payload} loading={loading} reportDate={reportDate} products={products} sendMode={sendMode} />
    </section>
  );
}
