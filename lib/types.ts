export type Concept = {
  id: string;
  name: string;
  group?: string;
  count?: number;
  reelFarmSyncedAt?: string;
};

export type Country = {
  id: string;
  name: string;
  reelFarmCode?: string;
  concepts?: Concept[];
  reelFarmSyncedAt?: string;
  creatorCount?: number;
  automationCount?: number;
  materialCount?: number;
  postCount?: number;
};

export type Product = {
  id: string;
  name: string;
  logo?: string;
  folder?: string;
  owner_type?: string;
  reelFarmCode?: string;
  countries?: Country[];
  countryCount?: number;
  creatorCount?: number;
  automationCount?: number;
  materialCount?: number;
  postCount?: number;
};

export type ProductKpis = {
  product_code?: string;
  today?: {
    creators?: number;
    posts?: number;
    views?: number;
    likes?: number;
    average_views?: number;
    utc_window?: { start?: string; end?: string };
  };
  seven_day?: {
    creators?: number;
    posts?: number;
    views?: number;
    likes?: number;
    average_creators?: number;
    average_posts?: number;
    average_views?: number;
    average_views_per_day?: number;
    average_likes?: number;
    average_er?: number;
    interactions?: number;
    utc_window?: { start?: string; end?: string };
  };
};

export type ProductGrowthSnapshot = {
  id?: string;
  product_code?: string;
  report_date?: string;
  report_timezone?: string;
  source_timezone?: string;
  utc_start?: string;
  utc_end?: string;
  source_date_from?: string;
  source_date_to?: string;
  reelfarm_views?: number | null;
  clone_views?: number | null;
  total_views?: number | null;
  download_count?: number | null;
  onboarding_unique?: number | null;
  synced_at?: string;
};

export type ProductGrowthPayload = {
  ok: boolean;
  product_code: string;
  report_timezone: string;
  source_timezone: string;
  date_from: string;
  date_to: string;
  latest?: ProductGrowthSnapshot;
  series: ProductGrowthSnapshot[];
  totals: {
    total_views?: number;
    reelfarm_views?: number;
    clone_views?: number;
    download_count?: number;
    onboarding_unique?: number;
  };
  generated_at?: string;
};

export type BusinessMaterialReportRow = {
  report_date: string;
  report_timezone?: string;
  business_window_local?: { start?: string; end?: string };
  onboarding_window_local?: { start?: string; end?: string };
  utc_window?: { start?: string; end?: string };
  onboarding_utc_window?: { start?: string; end?: string };
  source_date_from?: string;
  source_date_to?: string;
  reelfarm_materials?: number;
  reelfarm_expected_materials?: number;
  reelfarm_published_automations?: number;
  reelfarm_expected_automations?: number;
  reelfarm_posts?: number;
  reelfarm_views?: number;
  reelfarm_avg_views?: number | null;
  clone_materials?: number;
  clone_expected_materials?: number;
  clone_posts?: number;
  clone_views?: number;
  clone_avg_views?: number | null;
  total_materials?: number;
  expected_total_materials?: number;
  total_posts?: number;
  total_views?: number;
  downloads?: number | null;
  download_rate?: number | null;
  views_per_download?: number | null;
};

export type BusinessMaterialReportPayload = {
  ok: boolean;
  product_code: string;
  report_timezone: string;
  source_timezone: string;
  date_from: string;
  date_to: string;
  rows: BusinessMaterialReportRow[];
  totals: {
    reelfarm_materials?: number;
    reelfarm_expected_materials?: number;
    reelfarm_published_automations?: number;
    reelfarm_expected_automations?: number;
    reelfarm_posts?: number;
    reelfarm_views?: number;
    reelfarm_avg_views?: number | null;
    clone_materials?: number;
    clone_expected_materials?: number;
    clone_posts?: number;
    clone_views?: number;
    clone_avg_views?: number | null;
    expected_total_materials?: number;
    total_materials?: number;
    total_posts?: number;
    total_views?: number;
    downloads?: number;
    download_rate?: number | null;
  };
  generated_at?: string;
};

export type DailyFeishuTotals = {
  reelfarm_views?: number;
  clone_views?: number;
  total_views?: number;
  downloads?: number;
  download_rate?: number | null;
  [key: string]: unknown;
};

export type DailyFeishuProductSummary = {
  product_code?: string;
  product_name?: string;
  reelfarm_views?: number;
  clone_views?: number;
  total_views?: number;
  downloads?: number;
  download_rate?: number | null;
  errors?: string[];
  [key: string]: unknown;
};

export type FeishuSendMode = 'image' | 'card' | 'card_with_text_fallback' | 'template';

export type FeishuCardMetricProduct = {
  code?: string;
  name?: string;
  totalPosts?: number;
  totalPlays?: number;
  rfPlays?: number;
  clonePlays?: number;
  rfPublished?: number;
  rfExpected?: number;
  rfAvg?: number | null;
  cloneAvg?: number | null;
  onboarding?: number | null;
  downloadRate?: number | null;
  unsent?: number;
  zeroPlay?: number;
  countries?: Array<{
    flag?: string;
    name?: string;
    rfAvg?: number | null;
    posts?: number;
  }>;
  anomalyGroups?: Array<{
    title?: string;
    more?: string | null;
    accounts?: Array<{
      flag?: string;
      handle?: string;
      batch?: string;
    }>;
  }>;
};

export type FeishuCardTrendRow = {
  date?: string;
  label?: string;
  view?: number;
  download?: number;
};

export type FeishuCountryAvgTrend = {
  countryCode?: string;
  countryName?: string;
  flag?: string;
  rows?: Array<{
    date?: string;
    label?: string;
    rfAvg?: number | null;
    posts?: number;
  }>;
};

export type FeishuCardData = {
  bizDate?: string;
  window?: string;
  global?: {
    totalPlays?: number;
    rfPlays?: number;
    clonePlays?: number;
    rfPublished?: number;
    rfExpected?: number;
    rfAvg?: number | null;
    cloneAvg?: number | null;
    onboarding?: number | null;
    downloadRate?: number | null;
  };
  products?: FeishuCardMetricProduct[];
  trend?: FeishuCardTrendRow[];
  trendGroups?: Array<{
    key?: string;
    label?: string;
    trend?: FeishuCardTrendRow[];
  }>;
  countryAvgTrend?: Record<string, FeishuCountryAvgTrend[]>;
};

export type DailyFeishuReportError = {
  product_code?: string;
  product_name?: string;
  error?: string;
  [key: string]: unknown;
};

export type DailyFeishuReport = {
  report_date?: string;
  business_window_local?: { start?: string; end?: string };
  onboarding_window_local?: { start?: string; end?: string };
  totals?: DailyFeishuTotals;
  products?: DailyFeishuProductSummary[];
  errors?: DailyFeishuReportError[];
  generated_at?: string;
};

export type DailyFeishuPreviewPayload = {
  ok: boolean;
  report: DailyFeishuReport;
  message: string;
  message_preview?: string;
  mode?: FeishuSendMode;
  card_data?: FeishuCardData | null;
  card?: Record<string, unknown> | null;
  template_preview?: Record<string, unknown> | null;
};

export type DailyFeishuSendResult = {
  ok: boolean;
  sent_at?: string;
  report_date?: string;
  totals?: DailyFeishuTotals;
  product_count?: number;
  error_count?: number;
  message_preview?: string;
  mode?: FeishuSendMode;
  fallback_reason?: string;
  card_preview?: FeishuCardData | null;
  template_messages?: Record<string, string | undefined>;
  template_preview?: Record<string, unknown> | null;
  image_key?: string;
  message_id?: string;
  error?: string;
};

export type ProductRollupCountry = {
  country_id?: string;
  country_code?: string;
  country_name?: string;
  creator_count?: number;
  material_count?: number;
  post_count?: number;
  last_synced_at?: string;
  campaign_id?: string;
  campaign_name?: string;
  issues?: string[];
};

export type ProductRollup = {
  product_id?: string;
  product_code?: string;
  product_name?: string;
  source?: string;
  creator_count?: number;
  material_count?: number;
  post_count?: number;
  last_synced_at?: string;
  countries?: ProductRollupCountry[];
};

export type AccountSummary = {
  account_id: string;
  product_id?: string;
  product_code?: string;
  product_name?: string;
  country_id?: string;
  market_id?: string;
  country_code?: string;
  market_code?: string;
  country_name?: string;
  product_market_channel_id?: string;
  reelfarm_account_id?: string;
  museon_account_id?: string;
  username?: string;
  display_name?: string;
  avatar_url?: string;
  status?: string;
  automation_count?: number;
  automation_name?: string;
  automation_names?: string;
  post_mode?: string;
  publish_method?: string;
  material_count?: number;
  post_count?: number;
  posted_account_count?: number;
  expected_account_count?: number;
  total_views?: number;
  total_likes?: number;
  total_comments?: number;
  total_shares?: number;
  total_bookmarks?: number;
  latest_post_at?: string;
  last_synced_at?: string;
  data_source?: string;
  campaign_id?: string;
  campaign_name?: string;
};

export type MaterialRow = {
  id?: string;
  reelfarm_video_id?: string;
  video_type?: string;
  hook?: string;
  prompt?: string;
  slideshow_images?: Array<{ image_url?: string }>;
  slide_count?: number;
  status?: string;
  created_at?: string;
  finished_at?: string;
};

export type PostRow = {
  id?: string;
  reelfarm_post_id?: string;
  status?: string;
  title?: string;
  published_at?: string;
  published_at_meta?: string;
  published_at_readable?: string;
  synced_at?: string;
};

export type DetailedPostRow = {
  product?: Record<string, unknown>;
  country?: Record<string, unknown>;
  market?: Record<string, unknown>;
  account?: {
    id?: string;
    reelfarm_account_id?: string;
    museon_account_id?: string;
    username?: string;
    display_name?: string;
    avatar_url?: string;
    status?: string;
  };
  automation?: {
    id?: string;
    reelfarm_automation_id?: string;
    name?: string;
    status?: string;
    schedule?: unknown[];
  };
  material?: MaterialRow;
  post?: PostRow;
  metrics?: {
    view_count?: number;
    like_count?: number;
    comment_count?: number;
    share_count?: number;
    bookmark_count?: number;
  };
};

export type ReelFarmVideo = MaterialRow & {
  video_id?: string;
  finished?: boolean;
  failed?: boolean;
  video_url?: string | null;
};

export type ReelFarmPost = {
  post_id?: string;
  id?: string;
  video_id?: string;
  status?: string;
  title?: string;
  published_at?: string;
  published_at_meta?: string;
  published_at_readable?: string;
  view_count?: number;
  like_count?: number;
  comment_count?: number;
  share_count?: number;
  bookmark_count?: number;
};

export type ReelFarmCard = {
  card_key?: string;
  automation: {
    automation_id?: string;
    title?: string;
    status?: string;
    schedule?: unknown[];
    tiktok_account_id?: string;
  };
  account: {
    id?: string;
    account_id?: string;
    tiktok_account_id?: string;
    reelfarm_account_id?: string;
    account_name?: string;
    account_username?: string;
    username?: string;
    account_image?: string;
    avatar_url?: string;
    status?: string;
  };
  videos: ReelFarmVideo[];
  video_total?: number;
  posts: ReelFarmPost[];
  post_statistics?: Record<string, unknown>;
  summary_metrics?: {
    post_count?: number;
    material_count?: number;
    total_views?: number;
    total_likes?: number;
    total_comments?: number;
    total_shares?: number;
    total_bookmarks?: number;
  };
  tags?: string[];
  pagination?: {
    limit: number;
    offset: number;
    has_more: boolean;
    total?: number;
  };
  errors?: {
    videos?: string | null;
    posts?: string | null;
  };
};

export type ReelFarmResult = {
  prefix: string;
  count: number;
  cards: ReelFarmCard[];
  loading?: boolean;
  error?: string;
};

export type PublishCheckAssignment = {
  id: string;
  person_id: string;
  person_name: string;
  product_id: string;
  country_id: string;
};

export type PublishCheckAccount = {
  account_id?: string;
  reelfarm_account_id?: string;
  username?: string;
  display_name?: string;
  avatar_url?: string;
  account_status?: string;
  automation_id?: string;
  reelfarm_automation_id?: string;
  automation_name?: string;
  automation_status?: string;
  published_count?: number;
  today_latest_post_at?: string;
  latest_post_at?: string;
};

export type PublishCheckResult = {
  ok: boolean;
  generated_at?: string;
  beijing_date?: string;
  utc_window?: { start: string; end: string };
  totals?: {
    assignments: number;
    accounts: number;
    published_accounts: number;
    missing_accounts: number;
  };
  groups?: Array<{
    assignment_id?: string;
    person_id?: string;
    person_name?: string;
    product?: { id?: string; name?: string; code?: string; folder?: string };
    country?: { id?: string; name?: string; code?: string };
    account_count: number;
    published_account_count: number;
    missing_account_count: number;
    missing_accounts: PublishCheckAccount[];
  }>;
};

export type PublishCheckState = {
  assignments: PublishCheckAssignment[];
  last_result?: PublishCheckResult | null;
};

export type ExternalApiKey = {
  id: string;
  name: string;
  prefix: string;
  permissions: string[];
  active: boolean;
  created_at?: string;
  revoked_at?: string;
};

export type DatabaseSnapshot = {
  database_path?: string;
  database_backend?: string;
  table?: string;
  updated_at?: string;
  stats?: Record<string, number>;
  relational_tables?: Record<string, number>;
  data?: Product[];
};
