import type {
  AccountSummary,
  DetailedPostRow,
  ProductKpis,
  ProductRollup
} from '../types';

export type ApiResponseBase = {
  ok: boolean;
  error?: string;
  detail?: string;
  generated_at?: string;
};

export type DataQueryPagination = {
  limit: number;
  offset: number;
  has_more: boolean;
  total?: number;
};

export type DataQueryResponse<T> = ApiResponseBase & {
  resource?: string;
  filters?: Record<string, unknown>;
  data: T;
  pagination?: DataQueryPagination;
};

export type ProductKpisResponse = DataQueryResponse<ProductKpis>;
export type ProductRollupsResponse = DataQueryResponse<ProductRollup[]>;
export type AccountQueryResponse = DataQueryResponse<AccountSummary[]>;
export type DetailedRowsResponse = DataQueryResponse<DetailedPostRow[]> & {
  pagination: DataQueryPagination;
};

export type SyncResultResponse = ApiResponseBase & {
  source?: string;
  status?: string;
  product_code?: string;
  country_code?: string;
  started_at?: string;
  finished_at?: string;
  synced_at?: string;
  duration_seconds?: number | null;
  duration_total_seconds?: number | null;
  records_count?: number;
  errors?: Array<Record<string, unknown>>;
};

export type ReelfarmSyncCountryResponse = SyncResultResponse & {
  creator_count: number;
  material_count: number;
  product_cleanup?: Record<string, unknown>;
  relational_projection?: Record<string, unknown>;
};

export type MuseonSyncCountryResponse = SyncResultResponse & {
  skipped?: boolean;
  creator_count: number;
  material_count: number;
  post_count?: number;
};
