import { automationCoverageApi } from './automationCoverage';
import { authApi } from './auth';
import { catalogApi } from './catalog';
import { databaseApi } from './database';
import { dataQueryApi } from './dataQuery';
import { growthApi } from './growth';
import { geelarkApi } from './geelark';
import { reportsApi } from './reports';
import { syncApi } from './sync';
import { tagsApi } from './tags';

export { apiFetch, getErrorMessage, jsonPostInit, parseApiResponse, withQuery } from './client';

export const api = {
  ...authApi,
  ...catalogApi,
  ...dataQueryApi,
  ...growthApi,
  ...geelarkApi,
  ...reportsApi,
  ...syncApi,
  ...tagsApi,
  ...databaseApi,
  ...automationCoverageApi
};

export type ApiClient = typeof api;
