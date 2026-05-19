# Deca Growth Relational Database Schema

The current production database is Neon Postgres.

The relational tables below are the source of truth for synced ReelFarm data. The app may still keep the legacy `app_state` JSON record temporarily for frontend compatibility, but new ReelFarm syncs write into this schema directly.

## Core Model

```text
Product
  -> ProductMarket
    -> ProductMarketChannel
      -> Account
      -> Automation
        -> Material
          -> Post

Product
  -> Concept
    -> Format

Material
  -> Concept
  -> Format
```

## Tables

- `products`: apps/products such as Delust, DeenBack, Demi.
- `markets`: country or market dimension such as US, GE.
- `channels`: growth channels such as TikTok.
- `product_markets`: a product in a market, such as DeenBack + GE.
- `product_market_channels`: a product-market-channel combination, such as DeenBack + GE + TikTok.
- `accounts`: TikTok accounts under a product-market-channel combination.
- `automations`: ReelFarm automations tied to one account and one product-market-channel.
- `concepts`: product-level creative concepts.
- `formats`: formats under concepts.
- `materials`: ReelFarm-generated materials, owned by automation/account/product-market-channel and optionally classified into concept/format.
- `posts`: published post data and metrics for materials.

## Sync Behavior

ReelFarm sync is the write path for this schema:

```text
ReelFarm automation/account/videos/posts
  -> parse product + market from automation name
  -> upsert account / automation / material / post rows
```

There is no public rebuild endpoint in the app flow. Old JSON data is not the target schema.
