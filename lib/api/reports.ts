import type {
  BusinessMaterialReportPayload,
  DailyFeishuPreviewPayload,
  DailyFeishuSendResult,
  FeishuSendMode
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
  dailyFeishuPreview: (date?: string, mode?: FeishuSendMode) =>
    apiFetch<DailyFeishuPreviewPayload>(
      withQuery('/api/reports/daily-feishu-preview', new URLSearchParams({
        ...(date ? { date } : {}),
        ...(mode ? { mode } : {})
      })),
      undefined,
      'Failed to load Feishu report preview'
    ),
  sendDailyFeishuReport: (date?: string, options?: { mode?: FeishuSendMode }) =>
    apiFetch<DailyFeishuSendResult>(
      withQuery('/api/reports/daily-feishu', new URLSearchParams({
        ...(date ? { date } : {}),
        ...(options?.mode ? { mode: options.mode } : {})
      })),
      { method: 'POST' },
      'Failed to send Feishu daily report'
    )
};
