'use client';

import { useFeishuReport } from '@/hooks/useFeishuReport';
import {
  FeishuFlowGrid,
  FeishuReportHero
} from './FeishuReportParts';
import {
  FeishuAiPanel,
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
    model,
    setModel,
    modelOptions,
    modelListStatus,
    customModel,
    setCustomModel,
    includeAi,
    setIncludeAi,
    sendMode,
    setSendMode,
    analysisLoading,
    analysisPayload,
    analysisError,
    totals,
    products,
    downloadRate,
    selectedModel,
    loadPreview,
    sendReport,
    generateAnalysis
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
      <FeishuFlowGrid analysisPayload={analysisPayload} includeAi={includeAi} sendMode={sendMode} />
      <FeishuAiPanel
        model={model}
        setModel={setModel}
        modelOptions={modelOptions}
        modelListStatus={modelListStatus}
        customModel={customModel}
        setCustomModel={setCustomModel}
        includeAi={includeAi}
        setIncludeAi={setIncludeAi}
        sendMode={sendMode}
        analysisLoading={analysisLoading}
        loading={loading}
        analysisPayload={analysisPayload}
        analysisError={analysisError}
        selectedModel={selectedModel}
        generateAnalysis={generateAnalysis}
      />
      <FeishuReportSummary totals={totals} downloadRate={downloadRate} />
      <FeishuReportLayout payload={payload} loading={loading} reportDate={reportDate} products={products} sendMode={sendMode} />
    </section>
  );
}
