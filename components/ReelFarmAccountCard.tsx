'use client';

import { useState } from 'react';
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
  onMoveSlide,
  onAddTag,
  onRemoveTag,
  availableTags
}: {
  card: ReelFarmCard;
  isOpen: boolean;
  isLoading: boolean;
  slideIndexes: Record<string, number>;
  onToggle: (key: string) => void;
  onPage: (key: string, direction: number) => void;
  onMoveSlide: (videoId: string, direction: number, total: number) => void;
  onAddTag: (card: ReelFarmCard, tag: string) => void;
  onRemoveTag: (card: ReelFarmCard, tag: string) => void;
  availableTags: string[];
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [categoryInput, setCategoryInput] = useState('');
  const [tagInput, setTagInput] = useState('');
  const key = cardStateKey(card);
  const automation = card.automation || {};
  const account = card.account || {};
  const accountName = account.account_username || account.username || account.account_name || automation.tiktok_account_id || '未绑定账号';
  const displayAccount = String(accountName).startsWith('@') ? accountName : `@${accountName}`;
  const avatar = account.account_image ? <img src={account.account_image} alt="" /> : String(accountName || '?').replace('@', '').slice(0, 2).toUpperCase();
  const posts = card.posts || [];
  const videos = card.videos || [];
  const summary = card.summary_metrics || {};
  const tags = card.tags || [];
  const categories = Array.from(new Set(availableTags.map(getTagCategory).filter(Boolean)));
  const tagOptions = availableTags.filter(tag => !categoryInput.trim() || getTagCategory(tag).toLowerCase() === categoryInput.trim().toLowerCase());
  const views = Number(summary.total_views) || getMetricFromPosts(posts as any, 'view_count');
  const likes = Number(summary.total_likes) || getMetricFromPosts(posts as any, 'like_count');
  const comments = Number(summary.total_comments) || getMetricFromPosts(posts as any, 'comment_count');
  const shares = Number(summary.total_shares) || getMetricFromPosts(posts as any, 'share_count');
  const engagement = views > 0 ? ((likes + comments + shares) / views) * 100 : 0;
  const postMap = new Map(posts.map(post => [String(post.video_id), post]));
  const slideshows = videos.filter(video => postMap.has(String(video.video_id)));
  const pageSize = Number(card.pagination?.limit) || 4;
  const page = Math.max(0, Math.floor((Number(card.pagination?.offset) || 0) / pageSize));
  const total = Number(card.pagination?.total ?? summary.post_count ?? posts.length) || 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const stats: Array<[string, string]> = [
    ['Posts', formatNumber(Number(summary.post_count) || posts.length)],
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
        <div className="creator-inline-tags" onClick={event => event.stopPropagation()}>
          {tags.map(tag => (
            <button className="creator-tag-chip" style={tagChipStyle(tag)} type="button" key={tag} onClick={() => onRemoveTag(card, tag)} title="点击删除">
              {formatTagLabel(tag)} ×
            </button>
          ))}
          <button className="creator-tag-add" type="button" onClick={() => setPickerOpen(open => !open)} title="添加">+</button>
          {pickerOpen ? (
            <div className="tag-editor-backdrop" onClick={() => setPickerOpen(false)}>
              <div className="tag-editor-modal" onClick={event => event.stopPropagation()}>
                <button className="tag-editor-close" type="button" onClick={() => setPickerOpen(false)}>×</button>
                <h3>Edit Creator Tags</h3>
                <div className="tag-editor-section-title">Add Tag</div>
                <div className="tag-editor-row">
                  <label className="tag-editor-field">
                    <span>⌕</span>
                    <input
                      value={categoryInput}
                      onChange={event => setCategoryInput(event.target.value)}
                      placeholder="Category (search or type new)"
                      list={`tag-categories-${key}`}
                    />
                    <datalist id={`tag-categories-${key}`}>
                      {categories.map(category => <option value={category} key={category} />)}
                    </datalist>
                  </label>
                  <label className="tag-editor-field">
                    <span>⌕</span>
                    <input
                      value={tagInput}
                      onChange={event => setTagInput(event.target.value)}
                      placeholder={categoryInput.trim() ? 'Select or type tag' : 'Select category first...'}
                      list={`tag-options-${key}`}
                    />
                    <datalist id={`tag-options-${key}`}>
                      {tagOptions.map(option => <option value={getTagName(option)} key={option} />)}
                    </datalist>
                  </label>
                  <button
                    className="tag-editor-add"
                    type="button"
                    disabled={!categoryInput.trim() || !tagInput.trim()}
                    onClick={() => {
                      const nextTag = composeTag(categoryInput, tagInput);
                      onAddTag(card, nextTag);
                      setTagInput('');
                    }}
                  >
                    + Add
                  </button>
                </div>
                <div className="tag-editor-current">
                  {tags.length ? tags.map(tag => (
                    <button className="creator-tag-chip" style={tagChipStyle(tag)} type="button" key={tag} onClick={() => onRemoveTag(card, tag)}>
                      {formatTagLabel(tag)} ×
                    </button>
                  )) : <span className="creator-tag-empty">No tags yet</span>}
                </div>
                <div className="tag-editor-actions">
                  <button className="tag-editor-cancel" type="button" onClick={() => setPickerOpen(false)}>Cancel</button>
                  <button className="tag-editor-save" type="button" onClick={() => setPickerOpen(false)}>Save Tags</button>
                </div>
              </div>
            </div>
          ) : null}
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

function splitTag(value: string) {
  const [category, ...rest] = String(value || '').split(':');
  return {
    category: rest.length ? category.trim() : 'General',
    name: (rest.length ? rest.join(':') : category).trim()
  };
}

function getTagCategory(value: string) {
  return splitTag(value).category;
}

function getTagName(value: string) {
  return splitTag(value).name;
}

function composeTag(category: string, tag: string) {
  return `${category.trim()}: ${tag.trim()}`;
}

function formatTagLabel(value: string) {
  const { category, name } = splitTag(value);
  return `${category} · ${name}`;
}

function tagChipStyle(value: string) {
  const palette = [
    { bg: '#252044', border: '#6f63ff', color: '#c9c5ff' },
    { bg: '#15342a', border: '#38c78b', color: '#a8f0cc' },
    { bg: '#3a2415', border: '#f29b4b', color: '#ffd0a3' },
    { bg: '#3a1825', border: '#f06f9a', color: '#ffc1d3' },
    { bg: '#172d3d', border: '#5bbce9', color: '#b8eaff' }
  ];
  let hash = 0;
  for (const char of getTagCategory(value)) hash = char.charCodeAt(0) + ((hash << 5) - hash);
  const color = palette[Math.abs(hash) % palette.length];
  return { background: color.bg, borderColor: color.border, color: color.color };
}
