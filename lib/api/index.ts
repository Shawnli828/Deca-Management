import { authApi } from './auth';
import { catalogApi } from './catalog';
import { databaseApi } from './database';
import { dataQueryApi } from './dataQuery';
import { growthApi } from './growth';
import { publishCheckApi } from './publishCheck';
import { reportsApi } from './reports';
import { syncApi } from './sync';
import { tagsApi } from './tags';

export { apiFetch, jsonPostInit, parseApiResponse, withQuery } from './client';

export const api = {
  ...authApi,
  ...catalogApi,
  ...dataQueryApi,
  ...growthApi,
  ...reportsApi,
  ...syncApi,
  ...publishCheckApi,
  ...tagsApi,
  ...databaseApi
};

export type ApiClient = typeof api;
