import type { AccountSummary, DetailedPostRow, ReelFarmResult } from './types';

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
