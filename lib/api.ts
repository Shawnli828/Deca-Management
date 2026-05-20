import type {
  AccountSummary,
  DatabaseSnapshot,
  DetailedPostRow,
  ExternalApiKey,
  PublishCheckResult,
  PublishCheckState,
  Product,
  ProductKpis,
  ReelFarmResult,
  RoasterState
} from './types';

export async function parseApiResponse<T>(response: Response, fallback = 'Request failed'): Promise<T> {
  const text = await response.text();
  let payload: any = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      throw new Error(fallback);
    }
  }
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || fallback);
  }
  return payload as T;
}

async function apiFetch<T>(url: string, init?: RequestInit, fallback?: string) {
  return parseApiResponse<T>(await fetch(url, { cache: 'no-store', ...init }), fallback);
}

export const api = {
  login: (username: string, password: string) =>
    apiFetch<{ ok: boolean; authenticated: boolean }>('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }, '登录失败'),
  logout: () => fetch('/api/auth/logout', { method: 'POST', cache: 'no-store' }),
  data: () => apiFetch<{ data: Product[] }>('/api/data', undefined, 'Failed to load data'),
  saveData: (data: Product[]) =>
    apiFetch<{ data: Product[] }>('/api/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    }, 'Failed to save data'),
  reset: () => apiFetch<{ data: Product[] }>('/api/reset', { method: 'POST' }, 'Failed to reset'),
  dataQuery: <T>(params: URLSearchParams) => apiFetch<T>(`/api/data/query?${params.toString()}`),
  productKpis: (productCode: string) =>
    api.dataQuery<{ ok: boolean; data: ProductKpis }>(
      new URLSearchParams({ resource: 'product_kpis', product_code: productCode })
    ),
  accounts: (productCode: string, countryCode: string, days: number) =>
    api.dataQuery<{ ok: boolean; data: AccountSummary[] }>(
      new URLSearchParams({ resource: 'accounts', product_code: productCode, country_code: countryCode, days: String(days) })
    ),
  accountPosts: (productCode: string, countryCode: string, accountId: string, days: number, limit: number, offset: number) =>
    api.dataQuery<{ ok: boolean; data: DetailedPostRow[]; pagination: { limit: number; offset: number; has_more: boolean; total?: number } }>(
      new URLSearchParams({
        resource: 'account_posts',
        product_code: productCode,
        country_code: countryCode,
        account_id: accountId,
        days: String(days),
        limit: String(limit),
        offset: String(offset)
      })
    ),
  syncCountry: (payload: Record<string, unknown>) =>
    apiFetch<{ ok: boolean; creator_count: number; material_count: number; synced_at?: string }>('/api/reelfarm/sync-country', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }, 'Failed to sync ReelFarm country'),
  roaster: () => apiFetch<RoasterState>('/api/roaster', undefined, 'Failed to load roaster'),
  saveRoaster: (state: RoasterState) =>
    apiFetch<{ ok: boolean; state: RoasterState }>('/api/roaster', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state })
    }, 'Failed to save roaster'),
  publishCheck: () => apiFetch<{ ok: boolean; state: PublishCheckState }>('/api/publish-check', undefined, 'Failed to load publish check'),
  savePublishCheck: (state: PublishCheckState) =>
    apiFetch<{ ok: boolean; state: PublishCheckState }>('/api/publish-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state })
    }, 'Failed to save publish check'),
  runPublishCheck: () => apiFetch<PublishCheckResult>('/api/publish-check/run', { method: 'POST' }, 'Failed to run publish check'),
  sendPublishCheckReminder: () =>
    apiFetch<{ ok: boolean; sent_at?: string; missing_accounts?: number; message_preview?: string }>(
      '/api/publish-check/send-reminder',
      { method: 'POST' },
      'Failed to send Feishu reminder'
    ),
  database: () => apiFetch<DatabaseSnapshot>('/api/database', undefined, 'Failed to load database'),
  apiKeys: () => apiFetch<{ ok: boolean; keys: ExternalApiKey[] }>('/api/api-keys'),
  createApiKey: (name: string) =>
    apiFetch<{ ok: boolean; key: string; record: ExternalApiKey }>('/api/api-keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    }),
  revokeApiKey: (id: string) =>
    apiFetch<{ ok: boolean; record: ExternalApiKey }>('/api/api-keys/revoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    })
};

export function accountSummaryToCard(row: AccountSummary): ReelFarmResult['cards'][number] {
  const accountId = row.account_id || row.reelfarm_account_id || row.username || crypto.randomUUID();
  return {
    card_key: `account:${accountId}`,
    automation: {
      automation_id: accountId,
      title: row.username || row.display_name || row.reelfarm_account_id || accountId,
      status: row.status || 'unknown',
      schedule: []
    },
    account: {
      id: row.account_id,
      account_id: row.account_id,
      tiktok_account_id: row.reelfarm_account_id,
      reelfarm_account_id: row.reelfarm_account_id,
      account_name: row.display_name,
      account_username: row.username,
      username: row.username,
      account_image: row.avatar_url,
      avatar_url: row.avatar_url,
      status: row.status
    },
    videos: [],
    video_total: Number(row.material_count) || 0,
    posts: [],
    post_statistics: {},
    summary_metrics: {
      post_count: Number(row.post_count) || 0,
      material_count: Number(row.material_count) || 0,
      total_views: Number(row.total_views) || 0,
      total_likes: Number(row.total_likes) || 0,
      total_comments: Number(row.total_comments) || 0,
      total_shares: Number(row.total_shares) || 0,
      total_bookmarks: Number(row.total_bookmarks) || 0
    },
    pagination: { limit: 4, offset: 0, has_more: Number(row.post_count) > 4, total: Number(row.post_count) || 0 },
    errors: { videos: null, posts: null }
  };
}

export function mergePostRowsIntoCard(card: ReelFarmResult['cards'][number], rows: DetailedPostRow[]) {
  const videos = [];
  const posts = [];
  for (const row of rows) {
    const material = row.material || {};
    const post = row.post || {};
    const metrics = row.metrics || {};
    const videoId = material.reelfarm_video_id || material.id;
    const postId = post.reelfarm_post_id || post.id;
    if (row.automation) {
      card.automation = {
        automation_id: card.automation.automation_id || row.automation.reelfarm_automation_id || row.automation.id,
        title: row.automation.name || card.automation.title,
        status: row.automation.status || card.automation.status,
        schedule: row.automation.schedule || card.automation.schedule || []
      };
    }
    if (videoId) {
      videos.push({
        video_id: videoId,
        id: material.id,
        video_type: material.video_type,
        hook: material.hook,
        prompt: material.prompt,
        slideshow_images: material.slideshow_images || [],
        slide_count: Number(material.slide_count) || (material.slideshow_images || []).length,
        status: material.status,
        created_at: material.created_at,
        finished_at: material.finished_at,
        finished: material.status === 'Finished',
        failed: false,
        video_url: null
      });
    }
    if (postId) {
      posts.push({
        post_id: postId,
        id: post.id,
        video_id: videoId,
        status: post.status,
        title: post.title,
        published_at: post.published_at,
        published_at_meta: post.published_at,
        published_at_readable: post.published_at_readable,
        view_count: metrics.view_count,
        like_count: metrics.like_count,
        comment_count: metrics.comment_count,
        share_count: metrics.share_count,
        bookmark_count: metrics.bookmark_count
      });
    }
  }
  card.videos = videos;
  card.posts = posts;
  card.video_total = Math.max(Number(card.video_total) || 0, videos.length);
  return card;
}
