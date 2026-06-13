# RF Automation Lifecycle Notes

Updated: 2026-06-14

## Purpose

ReelFarm automations can disappear or change status after they have already produced materials/posts. The dashboard should show the current usable RF account pool, while historical materials and posts should remain in the database for reporting.

## Sync Behavior

- Each RF sync upserts every returned automation into `automations`.
- Returned automations are marked with:
  - `sync_status = present`
  - `last_seen_at = <sync time>`
  - `deleted_at = ""`
- After a successful country sync, existing automations for the same product/country that were not returned by RF are marked:
  - `sync_status = deleted`
  - `deleted_at = <first missing sync time>`
- Materials/posts/snapshots are not deleted when an automation is marked deleted.

## Dashboard Visibility

RF dashboard rows and stored RF card payloads only include automations where:

- `automation.status` is `active` or `paused`
- `automation.sync_status` is not `deleted`

This keeps archived, disabled, removed, or stale RF automations out of the live dashboard.

## Expected/Publish Check Count

Daily expected RF accounts use current active TikTok accounts:

- `automation.status = active`
- `automation.sync_status != deleted`
- counted by unique TikTok account, not raw automation id

This avoids double-counting when one TikTok account is attached to more than one automation.

## Historical Reporting

Existing materials, posts, and daily snapshots stay in the database. Historical reports can still read old records even if the producing automation later disappears from ReelFarm.
