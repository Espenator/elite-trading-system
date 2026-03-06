/**
 * dataSourcesApi.js - Data Sources Manager API Service
 * frontend-v2/src/services/dataSourcesApi.js
 *
 * Production-ready API client for the Data Sources Manager page.
 * Uses getApiUrl from config/api.js for environment-aware URL resolution.
 * In dev: Vite proxy forwards to backend. In prod: uses VITE_API_URL.
 */

import { getApiUrl, getAuthHeaders } from '../config/api';

const BASE = getApiUrl('dataSources');
const REQUEST_TIMEOUT_MS = 15000;

// Fallback data sources when backend is offline
const FALLBACK_SOURCES = [
  {id:"alpaca",name:"Alpaca Markets",category:"Market Data",status:"NO_CREDENTIALS",enabled:true,base_url:"https://paper-api.alpaca.markets",ws_url:"wss://stream.data.alpaca.markets/v2/iex",rate_limit:"200/min",polling_interval:"Real-time (WebSocket)",required_keys:["APCA_API_KEY_ID","APCA_API_SECRET_KEY"],credentials:{},config:{account_type:"paper"}},
  {id:"unusual_whales",name:"Unusual Whales",category:"Options Flow",status:"NO_CREDENTIALS",enabled:true,base_url:"https://api.unusualwhales.com",ws_url:"",rate_limit:"120/min",polling_interval:"30s",required_keys:["UW_API_TOKEN"],credentials:{},config:{}},
  {id:"finviz",name:"Finviz Elite",category:"Screener",status:"NO_CREDENTIALS",enabled:true,base_url:"https://elite.finviz.com",ws_url:"",rate_limit:"60/min",polling_interval:"5m",required_keys:["FINVIZ_EMAIL","FINVIZ_PASSWORD"],credentials:{},config:{}},
  {id:"fred",name:"FRED",category:"Macro",status:"NO_CREDENTIALS",enabled:true,base_url:"https://api.stlouisfed.org/fred",ws_url:"",rate_limit:"120/min",polling_interval:"1h",required_keys:["FRED_API_KEY"],credentials:{},config:{}},
  {id:"sec_edgar",name:"SEC EDGAR",category:"Filings",status:"NO_CREDENTIALS",enabled:true,base_url:"https://efts.sec.gov/LATEST",ws_url:"",rate_limit:"10/sec",polling_interval:"15m",required_keys:["SEC_USER_AGENT"],credentials:{},config:{}},
  {id:"stockgeist",name:"Stockgeist",category:"Sentiment",status:"NO_CREDENTIALS",enabled:true,base_url:"https://api.stockgeist.ai",ws_url:"wss://ws.stockgeist.ai",rate_limit:"100/min",polling_interval:"60s",required_keys:["STOCKGEIST_API_TOKEN"],credentials:{},config:{}},
  {id:"newsapi",name:"News API",category:"News",status:"NO_CREDENTIALS",enabled:true,base_url:"https://newsapi.org/v2",ws_url:"",rate_limit:"100/day",polling_interval:"15m",required_keys:["NEWS_API_KEY"],credentials:{},config:{}},
  {id:"discord",name:"Discord",category:"Social",status:"NO_CREDENTIALS",enabled:true,base_url:"https://discord.com/api/v10",ws_url:"wss://gateway.discord.gg",rate_limit:"50/sec",polling_interval:"Real-time (WebSocket)",required_keys:["DISCORD_BOT_TOKEN","DISCORD_CHANNEL_ID"],credentials:{},config:{}},
  {id:"twitter",name:"X/Twitter",category:"Social",status:"NO_CREDENTIALS",enabled:true,base_url:"https://api.twitter.com/2",ws_url:"",rate_limit:"300/15min",polling_interval:"60s",required_keys:["TWITTER_BEARER_TOKEN"],credentials:{},config:{}},
  {id:"youtube",name:"YouTube",category:"Knowledge",status:"NO_CREDENTIALS",enabled:true,base_url:"https://www.googleapis.com/youtube/v3",ws_url:"",rate_limit:"10000/day",polling_interval:"30m",required_keys:["YOUTUBE_API_KEY"],credentials:{},config:{}},
  {id:"reddit",name:"Reddit",category:"Social",status:"NO_CREDENTIALS",enabled:true,base_url:"https://oauth.reddit.com",ws_url:"",rate_limit:"60/min",polling_interval:"5m",required_keys:["REDDIT_CLIENT_ID","REDDIT_CLIENT_SECRET"],credentials:{},config:{}},
  {id:"polygon",name:"Polygon.io",category:"Market",status:"NO_CREDENTIALS",enabled:true,base_url:"https://api.polygon.io",ws_url:"wss://socket.polygon.io",rate_limit:"5/min (free)",polling_interval:"60s",required_keys:["POLYGON_API_KEY"],credentials:{},config:{}}
  ];

/** Enrich sources with locally-saved credential status */
function enrichWithLocalCreds(sources) {
    const saved = JSON.parse(localStorage.getItem('ds_credentials') || '{}');
    return sources.map(src => {
          const localCreds = saved[src.id];
          if (localCreds && Object.keys(localCreds).length > 0) {
                  return { ...src, status: 'CONFIGURED', credentials: localCreds };
          }
          return src;
    });
}

async function request(method, path, body = null) {
    const url = `${BASE}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const opts = {
        method,
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
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
        // BUG FIX: read body once with .text(), then try JSON.parse
      // (previously called .json() then .text() which fails because body is already consumed)
      const rawBody = await res.text();
        try {
                errorBody = JSON.parse(rawBody);
        } catch {
                errorBody = rawBody;
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
    list: async () => {
          try {
                  const data = await request('GET', '');
                  return enrichWithLocalCreds(data);
          } catch (e) {
                  console.warn('Backend offline, using fallback data sources:', e.message);
                  return enrichWithLocalCreds(FALLBACK_SOURCES);
          }
    },

    /** GET /data-sources/{id} - single source details */
    get: async (id) => {
          try {
                  return await request('GET', `/${id}`);
          } catch (e) {
                  const src = FALLBACK_SOURCES.find(s => s.id === id);
                  if (src) return src;
                  throw e;
          }
    },

    /** POST /data-sources/ - add new source */
    create: (source) => request('POST', '', source),

    /** PUT /data-sources/{id} - update source config */
    update: (id, updates) => request('PUT', `/${id}`, updates),

    /** DELETE /data-sources/{id} - remove source */
    remove: (id) => request('DELETE', `/${id}`),

    /** PUT /data-sources/{id}/credentials - encrypt & store keys */
    setCredentials: async (id, keys) => {
          try {
                  return await request('PUT', `/${id}/credentials`, { keys });
          } catch (e) {
                  console.warn('Backend offline, saving credentials locally');
                  const saved = JSON.parse(localStorage.getItem('ds_credentials') || '{}');
                  saved[id] = keys;
                  localStorage.setItem('ds_credentials', JSON.stringify(saved));
                  return { status: 'ok', message: 'Credentials saved locally (backend offline)' };
          }
    },

    /** GET /data-sources/{id}/credentials - get masked keys */
    getCredentials: (id) =>
          request('GET', `/${id}/credentials`),

    /** POST /data-sources/{id}/test - live connection test */
    test: async (id) => {
          try {
                  return await request('POST', `/${id}/test`);
          } catch (e) {
                  return { status: 'error', connected: false, message: 'Backend offline - cannot test connection' };
          }
    },

    /** POST /data-sources/ai-detect - detect provider from URL */
    aiDetect: (url) =>
          request('POST', '/ai-detect', { url }),
};

export default dataSources;
