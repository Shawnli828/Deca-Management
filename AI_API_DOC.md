# Deca Growth AI Read API

This document describes the read-only API for external AI tools to access Deca Growth material data.

The production backend is now served by FastAPI. Interactive API docs are available at:

```text
https://deca-management.vercel.app/api/docs
```

The OpenAPI schema is available at:

```text
https://deca-management.vercel.app/api/openapi.json
```

## Base URL

Production:

```text
https://deca-management.vercel.app
```

Local:

```text
http://127.0.0.1:8765
```

## Authentication

Recommended for external AI access:

```http
Authorization: Bearer YOUR_AI_API_KEY
```

Generate the API key inside the Deca Growth admin panel:

1. Log in to the Deca Growth dashboard.
2. Click `打开数据库`.
3. In `外部 AI API Keys`, enter a key name.
4. Click `生成 Key`.
5. Copy the generated key immediately. It is shown only once.

The generated key is stored in the database as a hash and can be revoked from the same panel.

`AI_API_KEY` in Vercel Environment Variables is still supported as a fallback, but it is no longer required for normal use.

## Endpoint

### GET `/api/ai/materials`

Returns country-level ReelFarm material data from the database.

This endpoint is read-only. It does not sync ReelFarm and does not modify the database.

### Query Parameters

| Parameter | Required | Example | Description |
| --- | --- | --- | --- |
| `product_code` | No | `DL` | Filter by product ReelFarm code. |
| `country_code` | No | `US` | Filter by country ReelFarm code. |
| `product_id` | No | `abc123` | Filter by internal product id. |
| `country_id` | No | `xyz789` | Filter by internal country id. |
| `synced_only` | No | `true` | Only return countries with synced ReelFarm cards. |
| `include_raw` | No | `true` | Include the raw stored ReelFarm result under `raw_reelfarm_result`. |

## Examples

### Get All Synced Materials

```bash
curl "https://deca-management.vercel.app/api/ai/materials?synced_only=true" \
  -H "Authorization: Bearer YOUR_AI_API_KEY"
```

### Get One Product/Country

```bash
curl "https://deca-management.vercel.app/api/ai/materials?product_code=DL&country_code=US" \
  -H "Authorization: Bearer YOUR_AI_API_KEY"
```

## Response Shape

```json
{
  "ok": true,
  "generated_at": "2026-05-19T03:20:00.000000+00:00",
  "database_backend": "postgres",
  "filters": {
    "product_code": "DL",
    "country_code": "US",
    "product_id": null,
    "country_id": null,
    "synced_only": true,
    "include_raw": false
  },
  "totals": {
    "products": 1,
    "countries": 1,
    "creators": 2,
    "materials": 18,
    "posts": 18
  },
  "countries": [
    {
      "product": {
        "id": "product-id",
        "name": "Delust",
        "folder": "甲方",
        "reelFarmCode": "DL"
      },
      "country": {
        "id": "country-id",
        "name": "United States",
        "reelFarmCode": "US"
      },
      "automation_prefix": "US-DL",
      "synced_at": "2026-05-19T03:20:00.000000+00:00",
      "creator_count": 2,
      "material_count": 18,
      "post_count": 18,
      "creators": [
        {
          "account": {
            "tiktok_account_id": "123",
            "account_username": "example_creator",
            "account_image": "https://..."
          },
          "automation": {
            "automation_id": "automation-id",
            "title": "US-DL-Discipline-Solution-1",
            "status": "active"
          },
          "material_count": 9,
          "post_count": 9,
          "materials": [
            {
              "video": {
                "video_id": "video-id",
                "video_type": "slideshow",
                "slideshow_images": [],
                "slide_count": 6,
                "hook": "First slide text",
                "prompt": "Full generation prompt..."
              },
              "post": {
                "post_id": "post-id",
                "video_id": "video-id",
                "published_at": "2026-05-17T19:52:50.25543+00:00",
                "published_at_meta": "2026-05-17T19:52:50.25543+00:00",
                "published_at_readable": "2026/05/17 19:52 UTC",
                "view_count": 787,
                "like_count": 99,
                "comment_count": 0,
                "share_count": 0,
                "bookmark_count": 19
              }
            }
          ]
        }
      ]
    }
  ]
}
```

## Notes For AI Classification

- Use `countries[].creators[].materials[]` as the main classification input.
- `video.prompt`, `video.hook`, `video.slideshow_images`, and `post` metrics are the most useful fields.
- `published_at_meta` is the original machine-readable timestamp.
- `published_at_readable` is the display-friendly UTC timestamp.
- The current data is country-level. Topic / Format classification can be generated later by AI from these materials.
