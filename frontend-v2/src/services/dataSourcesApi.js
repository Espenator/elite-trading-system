/**
 * dataSourcesApi.js - Data Sources Manager API Service
 * frontend-v2/src/services/dataSourcesApi.js
 *
 * Production-ready API client for the Data Sources Manager page.
 * Uses getApiUrl from config/api.js for environment-aware URL resolution.
 * In dev: Vite proxy forwards to backend. In prod: uses VITE_API_URL.
 */

import { getApiUrl } from '../config/api';

const BASE = getApiUrl('dataSources');
const REQUEST_TIMEOUT_MS = 15000;

async function request(method, path, body = null) {
  const url = `${BASE}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    signal: controller.signal,
  };
  if (body !== null) {
    opts.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, opts);
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error(`Request timeout after ${REQUEST_TIMEOUT_MS / 1000}s: ${method} ${path}`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!res.ok) {
    let errorBody;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = await res.text();
    }
    const msg = typeof errorBody === 'object'
      ? (errorBody.detail || JSON.stringify(errorBody))
      : errorBody;
    throw new Error(msg || `API ${method} ${path} failed (${res.status})`);
  }

  const text = await res.text();
  return text ? JSON.parse(text) : {};
}

const dataSources = {
  /** GET /data-sources/ - list all sources with health */
  list: () => request('GET', '/'),

  /** GET /data-sources/{id} - single source details */
  get: (id) => request('GET', `/${id}`),

  /** POST /data-sources/ - add new source */
  create: (source) => request('POST', '/', source),

  /** PUT /data-sources/{id} - update source config */
  update: (id, updates) => request('PUT', `/${id}`, updates),

  /** DELETE /data-sources/{id} - remove source */
  remove: (id) => request('DELETE', `/${id}`),

  /** PUT /data-sources/{id}/credentials - encrypt & store keys */
  setCredentials: (id, keys) =>
    request('PUT', `/${id}/credentials`, { keys }),

  /** GET /data-sources/{id}/credentials - get masked keys */
  getCredentials: (id) =>
    request('GET', `/${id}/credentials`),

  /** POST /data-sources/{id}/test - live connection test */
  test: (id) => request('POST', `/${id}/test`),

  /** POST /data-sources/ai-detect - detect provider from URL */
  aiDetect: (url) =>
    request('POST', '/ai-detect', { url }),
};

export default dataSources;
