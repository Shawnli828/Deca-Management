'use client';

import { useState } from 'react';
import type { Country, DetailedPostRow } from '@/lib/types';
import { countryFlag, formatNumber, formatUtcReadable } from '@/lib/utils';

export const ACCOUNT_POST_PAGE_SIZE = 4;

export type AccountPostState = {
  rows: DetailedPostRow[];
  loading: boolean;
  error: string;
  offset: number;
  hasMore: boolean;
  total?: number;
};

type AccountPostPanelRow = {
  account_id: string;
  username?: string | null;
  country: Country;
};

export function AccountPostPanel({
  row,
  state,
  onPage
}: {
  row: AccountPostPanelRow;
  state?: AccountPostState;
  onPage: (offset: number) => void;
}) {
  const rows = state?.rows || [];
  const offset = state?.offset || 0;
  const currentPage = Math.floor(offset / ACCOUNT_POST_PAGE_SIZE) + 1;
  const totalPages = state?.total ? Math.max(1, Math.ceil(state.total / ACCOUNT_POST_PAGE_SIZE)) : undefined;
  const canGoNext = Boolean(state?.hasMore)
    || (rows.length === ACCOUNT_POST_PAGE_SIZE && (!state?.total || offset + rows.length < state.total));

  return (
    <div className="pool-post-panel">
      <div className="pool-post-panel-head">
        <div>
          <strong>Posts by @{String(row.username || row.account_id).replace(/^@/, '')}</strong>
          <span>{countryFlag(row.country)} {row.country.name}</span>
        </div>
        <div className="pool-post-pager">
          <button className="pool-detail-btn" type="button" disabled={state?.loading || offset <= 0} onClick={() => onPage(Math.max(0, offset - ACCOUNT_POST_PAGE_SIZE))}>Previous</button>
          <span>{currentPage}{totalPages ? ` / ${totalPages}` : ''}</span>
          <button className="pool-detail-btn" type="button" disabled={state?.loading || !canGoNext} onClick={() => onPage(offset + ACCOUNT_POST_PAGE_SIZE)}>Next</button>
        </div>
      </div>

      {state?.loading ? <div className="pool-empty">Loading posts...</div> : null}
      {state?.error ? <div className="pool-empty">{state.error}</div> : null}
      {!state?.loading && !state?.error && !rows.length ? <div className="pool-empty">No posts found for this account.</div> : null}

      {rows.length ? (
        <div className="pool-post-grid">
          {rows.map(item => <PoolPostCard item={item} key={String(item.post?.id || item.post?.reelfarm_post_id || item.material?.id || item.material?.reelfarm_video_id)} />)}
        </div>
      ) : null}
    </div>
  );
}

function PoolPostCard({ item }: { item: DetailedPostRow }) {
  const material = item.material || {};
  const post = item.post || {};
  const metrics = item.metrics || {};
  const images = (Array.isArray(material.slideshow_images) ? material.slideshow_images : []) as Array<{ image_url?: string } | string>;
  const [slideIndex, setSlideIndex] = useState(0);
  const currentIndex = Math.min(slideIndex, Math.max(0, images.length - 1));
  const currentImage = images[currentIndex];
  const currentImageUrl = typeof currentImage === 'string' ? currentImage : currentImage?.image_url;
  const title = material.hook || post.title || material.reelfarm_video_id || post.reelfarm_post_id || 'Untitled post';
  const publishedAt = post.published_at_readable || formatUtcReadable(post.published_at || '');

  function moveSlide(direction: number) {
    if (images.length <= 1) return;
    setSlideIndex(previous => (previous + direction + images.length) % images.length);
  }

  return (
    <article className="pool-post-card">
      <div className="pool-post-thumb">
        {currentImageUrl ? (
          <>
            <img src={currentImageUrl} alt="" loading="lazy" decoding="async" />
            {images.length > 1 ? (
              <>
                <button className="slide-nav prev" type="button" onClick={() => moveSlide(-1)} aria-label="Previous slide">‹</button>
                <button className="slide-nav next" type="button" onClick={() => moveSlide(1)} aria-label="Next slide">›</button>
                <span className="slide-counter">{currentIndex + 1}/{images.length}</span>
              </>
            ) : null}
          </>
        ) : <span>No image</span>}
      </div>
      <div className="pool-post-body">
        <h3>{title}</h3>
        <p>{publishedAt ? `Published ${publishedAt}` : material.status || post.status || 'No publish time'}</p>
        <div className="pool-post-metrics">
          <span><strong>{formatNumber(metrics.view_count || 0)}</strong> Views</span>
          <span><strong>{formatNumber(metrics.like_count || 0)}</strong> Likes</span>
          <span><strong>{formatNumber(metrics.comment_count || 0)}</strong> Comments</span>
          <span><strong>{formatNumber(metrics.share_count || 0)}</strong> Shares</span>
        </div>
      </div>
    </article>
  );
}
