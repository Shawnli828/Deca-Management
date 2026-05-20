# Deca Growth Data API

This document explains how external tools, AI agents, scripts, and reporting jobs can read Deca Growth dashboard data.

The preferred API is:

```text
GET /api/data/query
```

The older endpoint `/api/ai/materials` remains available for backward compatibility, but new integrations should use `/api/data/query`.

## Base URLs

Production:

```text
https://deca-management.vercel.app
```

Local development:

```text
http://127.0.0.1:8765
```

Interactive FastAPI docs:

```text
https://deca-management.vercel.app/api/docs
```

OpenAPI schema:

```text
https://deca-management.vercel.app/api/openapi.json
```

## Authentication

External tools must send a dashboard-generated API key as a Bearer token:

```http
Authorization: Bearer YOUR_DECA_API_KEY
```

Generate a key in the Deca Growth dashboard:

1. Log in to the dashboard.
2. Click `打开数据库`.
3. Open `API Key`.
4. Enter a key name, for example `Classifier`.
5. Click `生成 Key`.
6. Copy the generated `deca_...` key immediately. It is shown only once.

Keys are stored as hashes and can be revoked from the same panel.

If your terminal cannot connect directly to Vercel from your local network, use your local proxy:

```bash
curl -x http://127.0.0.1:7897 \
  "https://deca-management.vercel.app/api/data/query?resource=summary" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

## General Response Format

Most successful `/api/data/query` responses use:

```json
{
  "ok": true,
  "resource": "posts",
  "filters": {
    "product_code": "DB",
    "country_code": "GE"
  },
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": true
  },
  "data": [],
  "generated_at": "2026-05-20T08:30:00.000000+00:00"
}
```

Error responses use:

```json
{
  "ok": false,
  "error": "Unauthorized"
}
```

Common errors:

| HTTP Status | Meaning |
| --- | --- |
| `401` | Missing, revoked, or invalid API key. |
| `400` | Unsupported resource, metric, or invalid query parameter. |
| `500` | Server/database error. Check Vercel runtime logs. |

## Important Rules

- `/api/data/query` is read-only.
- `/api/data/query` reads from the Deca Growth database only.
- It does not call ReelFarm.
- Sync endpoints are the only endpoints that fetch from ReelFarm.
- All timestamps stored from ReelFarm are UTC.
- Product/country codes are your internal ReelFarm codes, for example `DB`, `DL`, `DM`, `US`, `GE`, `FR`.

## Supported Query Parameters

| Parameter | Example | Applies To | Description |
| --- | --- | --- | --- |
| `resource` | `posts` | all | Required resource name. |
| `product_code` | `DB` | most | Filter by product code. |
| `country_code` | `GE` | most | Filter by country/market code. |
| `market_code` | `GE` | most | Alias for `country_code`. |
| `account_id` | `abc123` or `username` | accounts/posts/materials | Filter by internal account id, ReelFarm account id, or username. |
| `automation_id` | `rf-auto-id` | posts/materials | Filter by automation id. |
| `material_id` | `video-id` | posts/materials | Filter by material/video id. |
| `post_id` | `post-id` | posts/top_posts | Filter by post id. |
| `days` | `7` | accounts/account_posts/daily_metrics/posts/materials/top_posts | Relative UTC date window. |
| `date_from` | `2026-05-01` | posts/materials/top_posts | Inclusive lower date bound. |
| `date_to` | `2026-05-20` | posts/materials/top_posts | Inclusive upper date bound. |
| `metric` | `view_count` | top_posts | Sort metric. |
| `limit` | `50` | paginated resources | Default `50`, max `500`; `top_posts` max `100`. |
| `offset` | `0` | paginated resources | Pagination offset. |

## Resources

### 1. `resource=summary`

High-level totals across relational tables.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=summary" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Returns:

```json
{
  "ok": true,
  "resource": "summary",
  "data": {
    "products": 3,
    "countries": 7,
    "accounts": 234,
    "automations": 234,
    "materials": 8026,
    "posts": 8026,
    "total_views": 123456,
    "total_likes": 1234,
    "total_comments": 123,
    "total_shares": 12,
    "total_bookmarks": 45,
    "last_synced_at": "2026-05-20T08:00:00+00:00"
  }
}
```

Use this for health checks, reporting headers, and verifying that a key can access data.

### 2. `resource=countries`

Product/country rollups.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=countries&product_code=DB" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Returns rows with:

- `product_id`
- `product_code`
- `product_name`
- `country_id` / `market_id`
- `country_code` / `market_code`
- `country_name`
- `creator_count`
- `automation_count`
- `material_count`
- `post_count`
- total metrics
- `last_synced_at`

### 3. `resource=accounts`

Fast account summary rows for one product/country. This endpoint does not include posts or slideshow images.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=accounts&product_code=DB&country_code=GE&days=7" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Returns rows with:

- `account_id`
- `reelfarm_account_id`
- `username`
- `display_name`
- `avatar_url`
- `status`
- `automation_count`
- `material_count`
- `post_count`
- `total_views`
- `total_likes`
- `total_comments`
- `total_shares`
- `total_bookmarks`
- `latest_post_at`
- `last_synced_at`

Use this to render creator/account rows quickly.

### 4. `resource=account_posts`

Paginated post/material detail for one account.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=account_posts&product_code=DB&country_code=GE&account_id=user123&days=30&limit=4&offset=0" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Returns detailed rows with:

- `product`
- `country`
- `account`
- `automation`
- `material`
- `post`
- `metrics`
- `pagination`

Use this when a user expands one account and needs only that account's first page of posts.

### 5. `resource=posts`

Detailed post rows, filterable by product, country, account, automation, and date.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=posts&product_code=DB&country_code=GE&date_from=2026-04-30&limit=50" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Each row contains:

```json
{
  "product": { "id": "product-id", "code": "DB", "name": "DeenBack" },
  "country": { "id": "market-id", "code": "GE", "name": "Germany" },
  "account": {
    "id": "account-id",
    "reelfarm_account_id": "rf-account-id",
    "username": "creator_username",
    "display_name": "Creator Name",
    "avatar_url": "https://..."
  },
  "automation": {
    "id": "automation-id",
    "reelfarm_automation_id": "rf-automation-id",
    "name": "GE-DB-Fatih-Damage-44",
    "status": "active",
    "schedule": []
  },
  "material": {
    "id": "material-id",
    "reelfarm_video_id": "video-id",
    "video_type": "slideshow",
    "hook": "Hook text",
    "prompt": "Full prompt text",
    "slideshow_images": [{ "image_url": "https://..." }],
    "slide_count": 6,
    "status": "Finished",
    "created_at": "2026-05-17T19:52:01+00:00",
    "finished_at": "2026-05-17T19:52:20+00:00"
  },
  "post": {
    "id": "post-id",
    "reelfarm_post_id": "rf-post-id",
    "status": "published",
    "title": "Post title",
    "published_at": "2026-05-17T19:52:50.25543+00:00",
    "published_at_readable": "2026/05/17 19:52 UTC"
  },
  "metrics": {
    "view_count": 787,
    "like_count": 99,
    "comment_count": 0,
    "share_count": 0,
    "bookmark_count": 19
  }
}
```

Use this for AI classification because it includes the account, automation, hook, prompt, images, published time, and metrics.

### 6. `resource=materials`

Detailed material/video rows with related account, automation, product/country, and post if available.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=materials&product_code=DB&country_code=GE&limit=50" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Use this when the AI should classify generated assets even if you care more about video/material content than post metrics.

### 7. `resource=daily_metrics`

Daily trend data from `post_daily_snapshots`.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=daily_metrics&product_code=DB&country_code=GE&days=7" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Returns rows with:

- `snapshot_date`
- `post_count`
- `views`
- `likes`
- `comments`
- `shares`
- `bookmarks`
- `deltas`

Use this for daily performance deltas and trend reports.

### 8. `resource=top_posts`

Top posts sorted by one metric.

Supported metrics:

- `view_count`
- `like_count`
- `comment_count`
- `share_count`
- `bookmark_count`

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=top_posts&product_code=DB&country_code=GE&metric=view_count&limit=20" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Use this for best-performing material analysis.

### 9. `resource=country_cards`

Dashboard-compatible full country cards payload.

Example:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=country_cards&product_code=DB&country_code=GE" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Returns:

```json
{
  "prefix": "GE-DB",
  "count": 56,
  "cards": [
    {
      "automation": {},
      "account": {},
      "videos": [],
      "posts": [],
      "post_statistics": {},
      "errors": {}
    }
  ]
}
```

This resource is mainly for backward compatibility with the dashboard cards UI. It may be heavy for large countries. Prefer `accounts` + `account_posts` for progressive loading.

## Backward-Compatible Endpoint

### GET `/api/ai/materials`

This older endpoint returns a country-level nested payload.

Example:

```bash
curl "https://deca-management.vercel.app/api/ai/materials?product_code=DB&country_code=GE&synced_only=true" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

Use `/api/data/query?resource=posts` for new AI classification workflows.

## Recommended AI Classification Workflow

For classifying concept/format without writing back to the database:

1. Choose a product and country, for example `DB + GE`.
2. Query posts since the desired date:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=posts&product_code=DB&country_code=GE&date_from=2026-04-30&limit=500" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```

3. For each row, read:
   - `product.code`, `product.name`
   - `country.code`, `country.name`
   - `account.username`
   - `automation.name`
   - `material.hook`
   - `material.prompt`
   - `material.slideshow_images`
   - `post.published_at`
   - `metrics`

4. Ask the AI to classify each material into:
   - `concept`
   - `format`
   - optional confidence/explanation

5. Keep the returned classification outside the database until you are ready to implement a write-back endpoint.

## Quick Test Commands

Health check, no key required:

```bash
curl "https://deca-management.vercel.app/api/health"
```

Unauthorized check:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=summary"
```

Authorized summary:

```bash
curl "https://deca-management.vercel.app/api/data/query?resource=summary" \
  -H "Authorization: Bearer YOUR_DECA_API_KEY"
```
