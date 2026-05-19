# Deca Growth Relational Database Schema

The current production database is Neon Postgres.

The app still keeps the legacy `app_state` JSON record for frontend compatibility, but the database now also has relational tables for the long-term data model.

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

## Rebuild Endpoint

The relational tables can be rebuilt from the current saved dashboard JSON:

```http
POST /api/database/rebuild-relational
```

This does not delete `app_state`; it only rebuilds the relational projection tables.

Normal ReelFarm sync now also writes into these relational tables automatically. The rebuild endpoint is only for backfilling or repairing old saved JSON data.

For large datasets, rebuild one product/market at a time:

```http
POST /api/database/rebuild-relational?product_code=DL&country_code=US&reset=false
```
