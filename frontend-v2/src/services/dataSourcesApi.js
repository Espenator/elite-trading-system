/**
 * dataSourcesApi.js - Data Sources Manager API Service
 * frontend-v2/src/services/dataSourcesApi.js
 *
 * Standalone API client for the Data Sources Manager page.
 * All calls go through the backend at VITE_API_URL (default localhost:8000).
 */

import { getApiUrl } from '../config/api';

const API_BASE = getApiUrl('dataSources') || 'http://localhost:8000/api/v1/data-sources';

async function request(method, path, body = null) {
  const url = `http://localhost:8000${path}`;
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== null) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API ${method} ${path} failed (${res.status}): ${errorBody}`);
  }
  return res.json();
}

const dataSources = {
  /** GET /api/v1/data-sources/ - list all sources with health */
  list: () => request('GET', '/api/v1/data-sources/'),

  /** GET /api/v1/data-sources/{id} - single source details */
  get: (id) => request('GET', `/api/v1/data-sources/${id}`),

  /** POST /api/v1/data-sources/ - add new source */
  create: (source) => request('POST', '/api/v1/data-sources/', source),

  /** PUT /api/v1/data-sources/{id} - update source config */
  update: (id, updates) => request('PUT', `/api/v1/data-sources/${id}`, updates),

  /** DELETE /api/v1/data-sources/{id} - remove source */
  remove: (id) => request('DELETE', `/api/v1/data-sources/${id}`),

  /** PUT /api/v1/data-sources/{id}/credentials - encrypt & store keys */
  setCredentials: (id, keys) =>
    request('PUT', `/api/v1/data-sources/${id}/credentials`, { keys }),

  /** GET /api/v1/data-sources/{id}/credentials - get masked keys */
  getCredentials: (id) =>
    request('GET', `/api/v1/data-sources/${id}/credentials`),

  /** POST /api/v1/data-sources/{id}/test - live connection test */
  test: (id) => request('POST', `/api/v1/data-sources/${id}/test`),

  /** POST /api/v1/data-sources/ai-detect - detect provider from URL */
  aiDetect: (url) =>
    request('POST', '/api/v1/data-sources/ai-detect', { url }),
};

export default dataSources;
