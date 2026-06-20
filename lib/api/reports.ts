import type {
  BusinessMaterialReportPayload,
  DailyFeishuAnalysisPayload,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  LlmModelsPayload
} from '../types';
import { apiFetch, withQuery } from './client';

export const reportsApi = {
  businessMaterialReport: (productCode: string, params: { days?: number; dateFrom?: string; dateTo?: string; mode?: string }) =>
    apiFetch<BusinessMaterialReportPayload>(
      withQuery('/api/business-material-report', new URLSearchParams({
        product_code: productCode,
        ...(params.mode ? { mode: params.mode } : {}),
        ...(params.dateFrom ? { date_from: params.dateFrom } : {}),
        ...(params.dateTo ? { date_to: params.dateTo } : {}),
        ...(!params.dateFrom && !params.dateTo ? { days: String(params.days || 7) } : {})
      })),
      undefined,
      'Failed to load business day report'
    ),
  dailyFeishuPreview: (date?: string) =>
    apiFetch<DailyFeishuPreviewPayload>(
      withQuery('/api/reports/daily-feishu-preview', new URLSearchParams(date ? { date } : {})),
      undefined,
      'Failed to load Feishu report preview'
    ),
  dailyFeishuAnalysis: (date?: string, model?: string) =>
    apiFetch<DailyFeishuAnalysisPayload>(
      withQuery('/api/reports/daily-feishu-analysis', new URLSearchParams({
        ...(date ? { date } : {}),
        ...(model ? { model } : {})
      })),
      { method: 'POST' },
      'Failed to generate Feishu AI analysis'
    ),
  llmModels: () =>
    apiFetch<LlmModelsPayload>('/api/reports/llm-models', undefined, 'Failed to load LLM models'),
  sendDailyFeishuReport: (date?: string, options?: { includeAi?: boolean; model?: string }) =>
    apiFetch<DailyFeishuSendResult>(
      withQuery('/api/reports/daily-feishu', new URLSearchParams({
        ...(date ? { date } : {}),
        ...(options?.includeAi ? { include_ai: '1' } : {}),
        ...(options?.model ? { model: options.model } : {})
      })),
      { method: 'POST' },
      'Failed to send Feishu daily report'
    )
};
