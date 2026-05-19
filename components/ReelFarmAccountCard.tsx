'use client';

import type { ReelFarmCard } from '@/lib/types';
import { cardStateKey, formatNumber, formatPercent, getMetricFromPosts } from '@/lib/utils';
import { MaterialCard } from './MaterialCard';

export function ReelFarmAccountCard({
  card,
  isOpen,
  isLoading,
  slideIndexes,
  onToggle,
  onPage,
  onMoveSlide
}: {
  card: ReelFarmCard;
  isOpen: boolean;
  isLoading: boolean;
  slideIndexes: Record<string, number>;
  onToggle: (key: string) => void;
  onPage: (key: string, direction: number) => void;
  onMoveSlide: (videoId: string, direction: number, total: number) => void;
}) {
  const key = cardStateKey(card);
  const automation = card.automation || {};
  const account = card.account || {};
  const accountName = account.account_username || account.username || account.account_name || automation.tiktok_account_id || '未绑定账号';
  const displayAccount = String(accountName).startsWith('@') ? accountName : `@${accountName}`;
  const avatar = account.account_image ? <img src={account.account_image} alt="" /> : String(accountName || '?').replace('@', '').slice(0, 2).toUpperCase();
  const posts = card.posts || [];
  const videos = card.videos || [];
  const summary = card.summary_metrics || {};
  const views = Number(summary.total_views) || getMetricFromPosts(posts as any, 'view_count');
  const likes = Number(summary.total_likes) || getMetricFromPosts(posts as any, 'like_count');
  const comments = Number(summary.total_comments) || getMetricFromPosts(posts as any, 'comment_count');
  const shares = Number(summary.total_shares) || getMetricFromPosts(posts as any, 'share_count');
  const engagement = views > 0 ? ((likes + comments + shares) / views) * 100 : 0;
  const postMap = new Map(posts.map(post => [String(post.video_id), post]));
  const slideshows = videos.filter(video => postMap.has(String(video.video_id)));
  const pageSize = Number(card.pagination?.limit) || 4;
  const page = Math.max(0, Math.floor((Number(card.pagination?.offset) || 0) / pageSize));
  const totalPages = Math.max(1, page + (card.pagination?.has_more ? 2 : 1));
  const stats: Array<[string, string]> = [
    ['Posts', formatNumber(Number(summary.post_count) || posts.length)],
    ['Slides', formatNumber(Number(summary.material_count) || Number(card.video_total) || slideshows.length)],
    ['Views', formatNumber(views)],
    ['Likes', formatNumber(likes)],
    ['Comments', formatNumber(comments)],
    ['Shares', formatNumber(shares)],
    ['Engagement', formatPercent(engagement)]
  ];

  return (
    <article className={`reelfarm-card ${isOpen ? 'is-open' : ''}`}>
      <div className="creator-header" role="button" tabIndex={0} onClick={() => onToggle(key)} onKeyDown={event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onToggle(key);
        }
      }}>
        <div className="reelfarm-account">
          <span className="reelfarm-avatar">{avatar}</span>
          <span className="creator-meta">
            <span className="creator-name-line">
              <span className="creator-name">{accountName}</span>
              <span className="creator-chip">{automation.status || 'unknown'}</span>
            </span>
            <span className="creator-subline">{displayAccount}</span>
          </span>
        </div>
        {stats.map(([label, value]) => (
          <div className="creator-stat" key={label}>
            <div className="creator-stat-value">{value}</div>
            <div className="creator-stat-label">{label}</div>
          </div>
        ))}
        <span className="creator-expand">›</span>
      </div>
      <div className="creator-row-subtitle">{automation.title || automation.automation_id || 'Untitled automation'}</div>
      {isOpen ? (
        <>
          <div className="creator-toolbar">
            <div className="creator-toolbar-title">Posts by {displayAccount}</div>
            <div className="creator-toolbar-pill">Recently Published</div>
          </div>
          <div className="slideshow-list">
            {isLoading ? (
              <div className="empty-state compact"><div className="empty-title">Loading posts...</div></div>
            ) : slideshows.length ? (
              slideshows.map(video => (
                <MaterialCard
                  key={video.video_id || video.id}
                  video={video}
                  post={postMap.get(String(video.video_id))}
                  accountName={accountName}
                  avatar={avatar}
                  slideIndex={slideIndexes[String(video.video_id || video.id)] || 0}
                  onMoveSlide={onMoveSlide}
                />
              ))
            ) : (
              <div className="item-meta" style={{ color: '#bfb7ad' }}>暂无素材数据</div>
            )}
          </div>
          {card.pagination && (page > 0 || card.pagination.has_more) ? (
            <div className="post-pager">
              <span>{page + 1}/{totalPages}</span>
              <div className="post-pager-controls">
                <button className="post-page-btn" type="button" disabled={page === 0} onClick={() => onPage(key, -1)}>Previous</button>
                <button className="post-page-btn" type="button" disabled={!card.pagination.has_more} onClick={() => onPage(key, 1)}>Next</button>
              </div>
            </div>
          ) : null}
          {card.errors?.posts ? <div className="item-meta" style={{ padding: '0 14px 14px', color: '#bfb7ad' }}>{card.errors.posts}</div> : null}
        </>
      ) : null}
    </article>
  );
}
