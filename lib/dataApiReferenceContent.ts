export const dataApiBaseUrl = 'https://deca-management.vercel.app';

export const dataApiResourceCatalog = [
  ['summary', '中台总览数据'],
  ['countries', '产品 × 国家汇总'],
  ['accounts', '账号摘要列表'],
  ['account_posts', '单账号分页 posts'],
  ['posts', '详细 post rows'],
  ['materials', '素材/video rows'],
  ['daily_metrics', '每日快照趋势'],
  ['top_posts', '高表现内容'],
  ['country_cards', '兼容旧卡片结构']
];

export const dataApiExamples = {
  authCurl: `curl -X GET ${dataApiBaseUrl}/api/data/query?resource=summary \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`,
  accountsCurl: `curl "${dataApiBaseUrl}/api/data/query?resource=accounts&product_code=DB&country_code=GE&days=7" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`,
  postsCurl: `curl "${dataApiBaseUrl}/api/data/query?resource=posts&product_code=DB&country_code=GE&date_from=2026-04-30&limit=50" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`,
  accountPostsCurl: `curl "${dataApiBaseUrl}/api/data/query?resource=account_posts&product_code=DB&country_code=GE&account_id=user123&limit=4&offset=0" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`,
  materialsCurl: `curl "${dataApiBaseUrl}/api/data/query?resource=materials&product_code=DB&country_code=GE&limit=50" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`,
  dailyMetricsCurl: `curl "${dataApiBaseUrl}/api/data/query?resource=daily_metrics&product_code=DB&country_code=GE&days=7" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`,
  topPostsCurl: `curl "${dataApiBaseUrl}/api/data/query?resource=top_posts&product_code=DB&country_code=GE&metric=view_count&limit=20" \\
  -H "Authorization: Bearer YOUR_DECA_API_KEY"`
};

export const dataApiResponseExamples = {
  summary: `{
  "ok": true,
  "resource": "summary",
  "data": {
    "products": 3,
    "accounts": 234,
    "posts": 8026,
    "total_views": 123456
  }
}`,
  error: `{
  "ok": false,
  "error": "Unauthorized"
}`
};
