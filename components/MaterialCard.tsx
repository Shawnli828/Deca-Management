'use client';

import type { ReelFarmPost, ReelFarmVideo } from '@/lib/types';
import { formatNumber, formatUtcReadable } from '@/lib/utils';

export function MaterialCard({
  video,
  post,
  accountName,
  avatar,
  slideIndex,
  onMoveSlide
}: {
  video: ReelFarmVideo;
  post?: ReelFarmPost;
  accountName: string;
  avatar: React.ReactNode;
  slideIndex: number;
  onMoveSlide: (videoId: string, direction: number, total: number) => void;
}) {
  const title = video.hook || post?.title || video.video_id || video.id || 'Slideshow';
  const images = Array.isArray(video.slideshow_images) ? video.slideshow_images : [];
  const imageCount = video.slide_count || images.length;
  const currentIndex = Math.min(slideIndex, Math.max(0, images.length - 1));
  const current = images[currentIndex];
  const displayAccount = String(accountName || '').startsWith('@') ? accountName : `@${accountName || 'unknown'}`;
  const publishedReadable = post?.published_at_readable || formatUtcReadable(post?.published_at_meta || post?.published_at || '');
  const dataRows: Array<[string, unknown]> = [
    ['Views', post?.view_count],
    ['Likes', post?.like_count],
    ['Comments', post?.comment_count],
    ['Shares', post?.share_count],
    ['Saves', post?.bookmark_count]
  ];

  return (
    <div className="slideshow-item">
      <div className="slideshow-card-head">
        <div className="slideshow-card-account">
          <span className="reelfarm-avatar">{avatar}</span>
          <span>{displayAccount}</span>
        </div>
        <span className="tiktok-pill">♪</span>
      </div>
      <div className="material-preview">
        {current?.image_url ? (
          <>
            <img src={current.image_url} alt="" loading="lazy" decoding="async" />
            {images.length > 1 ? (
              <>
                <button className="slide-nav prev" type="button" onClick={() => onMoveSlide(String(video.video_id || video.id), -1, images.length)}>‹</button>
                <button className="slide-nav next" type="button" onClick={() => onMoveSlide(String(video.video_id || video.id), 1, images.length)}>›</button>
                <span className="slide-counter">{currentIndex + 1}/{images.length}</span>
              </>
            ) : null}
          </>
        ) : (
          <div className="empty-state" style={{ padding: '32px 12px' }}>
            <div className="empty-title">暂无图片</div>
          </div>
        )}
      </div>
      <div className="slideshow-body">
        <div className="slideshow-title">{title}</div>
        <div className="slideshow-meta">{imageCount ? `${imageCount} slides` : video.status || 'unknown'}</div>
        <div className="material-data">
          {dataRows.map(([label, value]) => (
            <div className="material-data-cell" key={label}>
              <div className="material-data-label">{label}</div>
              <div className="material-data-value">{post ? formatNumber(value) : '—'}</div>
            </div>
          ))}
        </div>
        <div className="slideshow-footer">
          <span>{publishedReadable ? `Published ${publishedReadable}` : '暂无 TikTok 发布数据'}</span>
          <span>{video.status || ''}</span>
        </div>
      </div>
    </div>
  );
}
