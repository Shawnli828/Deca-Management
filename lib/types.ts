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
  materialCount?: number;
};

export type Product = {
  id: string;
  name: string;
  logo?: string;
  folder?: string;
  owner_type?: string;
  reelFarmCode?: string;
  countries?: Country[];
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
  pagination?: {
    limit: number;
    offset: number;
    has_more: boolean;
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
