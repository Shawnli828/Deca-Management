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

export type TagDashboardAccount = {
  account_id: string;
  username?: string;
  display_name?: string;
  avatar_url?: string;
  status?: string;
  post_count?: number;
  total_views?: number;
  latest_post_at?: string;
};

export type TagDashboardCountry = {
  country_id?: string;
  country_name?: string;
  country_code?: string;
  account_count?: number;
  yesterday_avg_views?: number;
  seven_day_avg_views?: number;
  seven_day_er?: number;
  accounts: TagDashboardAccount[];
};

export type TagDashboardItem = {
  tag: string;
  account_count: number;
  yesterday_avg_views: number;
  seven_day_avg_views: number;
  seven_day_er: number;
  countries: TagDashboardCountry[];
};

export type TagDashboard = {
  ok: boolean;
  product_code: string;
  windows?: Record<string, string>;
  tags: TagDashboardItem[];
};

export type AccountSummary = {
  account_id: string;
  reelfarm_account_id?: string;
  username?: string;
  display_name?: string;
  avatar_url?: string;
  status?: string;
  automation_count?: number;
  material_count?: number;
  post_count?: number;
  total_views?: number;
  total_likes?: number;
  total_comments?: number;
  total_shares?: number;
  total_bookmarks?: number;
  latest_post_at?: string;
  last_synced_at?: string;
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

export type RoasterState = {
  people: Array<{ id: string; name: string }>;
  assignments: Record<string, Record<string, string[]>>;
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
