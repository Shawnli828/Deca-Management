import { parseApiResponse } from '../lib/api/client';
import { cloudProductsFrom, productCountryPairs } from '../lib/domain/cloudPhoneMap';
import { syncStatusPillState, syncStatusSources } from '../lib/domain/syncStatus';
import { reportTotals, ratio } from '../lib/feishuReportHelpers';
import { accountSummaryToCard, mergePostRowsIntoCard } from '../lib/reelfarmCardAdapters';
import { mergeAccountPostRowsIntoResults } from '../lib/reelFarmDashboardState';
import type { AccountSummary, Country, DetailedPostRow, Product } from '../lib/types';

function assertTrue(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function assertRejects(fn: () => Promise<unknown>, message: string) {
  try {
    await fn();
  } catch {
    return;
  }
  throw new Error(message);
}

async function checkApiParsing() {
  const ok = await parseApiResponse<{ ok: boolean; value: number }>(
    new Response(JSON.stringify({ ok: true, value: 7 }), { status: 200 }),
    'fallback'
  );
  assertTrue(ok.value === 7, 'api parser should preserve JSON payload fields');

  await assertRejects(
    () => parseApiResponse(new Response(JSON.stringify({ ok: false, detail: 'bad input' }), { status: 200 }), 'fallback'),
    'api parser should reject ok:false payloads'
  );
}

function checkCloudPhoneDomain() {
  const product: Product = {
    id: 'product-demi',
    name: 'Demi',
    reelFarmCode: 'DM',
    countries: [{ id: 'country-ge', name: 'Germany', reelFarmCode: 'GE' }]
  };
  const pairs = productCountryPairs([product]);
  assertTrue(pairs.length === 1 && pairs[0].productCode === 'DM' && pairs[0].countryCode === 'GE', 'cloud phone pairs should use ReelFarm codes');

  const cloudProducts = cloudProductsFrom([product], {
    'DM:GE': {
      ok: true,
      phone_count: 1,
      group_count: 1,
      filters: { product_code: 'DM', country_code: 'GE' },
      groups: [{
        id: 'group-1',
        name: 'Zhan-GE-01-DM',
        productCode: 'DM',
        countryCode: 'GE',
        phones: [{ id: 'phone-1', serialNo: '001', status: 2, rpaStatus: 0 }]
      }]
    }
  });
  assertTrue(cloudProducts[0].ipGroups[0].slots[0].serialNo === '001', 'cloud phone payload should map GeeLark phones into slots');
}

function checkFeishuHelpers() {
  const totals = reportTotals({ totals: { total_views: 1200, download_rate: 2.5 } });
  assertTrue(totals.total_views === 1200, 'Feishu totals helper should expose report totals');
  assertTrue(ratio('2.5') === 2.5, 'Feishu ratio should parse numeric strings');
  assertTrue(ratio('not-a-number') === null, 'Feishu ratio should reject invalid values');
}

function checkReelFarmAdapters() {
  const product: Product = { id: 'product-demi', name: 'Demi', reelFarmCode: 'DM' };
  const country: Country = { id: 'country-ge', name: 'Germany', reelFarmCode: 'GE' };
  const account: AccountSummary = {
    account_id: 'account-1',
    username: 'demi_test',
    status: 'active',
    post_count: 3,
    material_count: 5,
    total_views: 900
  };
  const card = accountSummaryToCard(account);
  const rows: DetailedPostRow[] = [{
    automation: { id: 'automation-1', name: 'GE-DM-test', status: 'active' },
    material: { id: 'material-1', reelfarm_video_id: 'video-1', status: 'Finished', slideshow_images: [{ image_url: 'https://example.com/1.png' }] },
    post: { id: 'post-1', reelfarm_post_id: 'post-1', published_at_readable: 'today' },
    metrics: { view_count: 100, like_count: 10 }
  }];
  mergePostRowsIntoCard(card, rows);
  assertTrue(card.posts.length === 1 && card.videos.length === 1, 'ReelFarm card adapter should merge post rows into card media');

  const results = mergeAccountPostRowsIntoResults({
    results: {
      'GE-DM': { prefix: 'GE-DM', count: 1, cards: [card] }
    },
    product,
    country,
    cardKey: card.card_key || '',
    data: rows,
    pagination: { limit: 4, offset: 0, has_more: false, total: 1 }
  });
  assertTrue(results['GE-DM'].cards[0].pagination?.total === 1, 'ReelFarm dashboard state should preserve post pagination');
}

function checkSyncStatusDomain() {
  const sources = syncStatusSources({
    ok: true,
    sources: {
      reelfarm: { label: 'ReelFarm', status: 'success' },
      museon_clone: { label: 'Museon', status: 'failed' }
    }
  });
  assertTrue(syncStatusPillState(sources.reelfarm) === 'fresh', 'sync status should map success to fresh');
  assertTrue(syncStatusPillState(sources.museon_clone) === 'error', 'sync status should map non-success status to error');
  assertTrue(syncStatusPillState(undefined) === 'missing', 'sync status should default missing source to missing');
}

async function main() {
  await checkApiParsing();
  checkCloudPhoneDomain();
  checkFeishuHelpers();
  checkReelFarmAdapters();
  checkSyncStatusDomain();

  console.log('frontend regression checks passed');
}

void main();
