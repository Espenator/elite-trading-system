/**
 * Embodier Trader Mobile — PWA app logic.
 * Calls /api/v1/mobile/* with Bearer token; auto-refresh every 15s.
 */

const API_BASE = '/api/v1/mobile';
const STORAGE_KEY = 'embodier_mobile_token';
const REFRESH_INTERVAL_MS = 15 * 1000;
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 2000;

let refreshTimer = null;
let pendingConfirm = null;

// ─── Token ─────────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem(STORAGE_KEY);
}

function setToken(value) {
  if (value) localStorage.setItem(STORAGE_KEY, value);
  else localStorage.removeItem(STORAGE_KEY);
}

function ensureToken() {
  const token = getToken();
  if (token) return Promise.resolve(token);
  return new Promise((resolve) => {
    const modal = document.getElementById('token-modal');
    const input = document.getElementById('token-input');
    const saveBtn = document.getElementById('token-save');
    modal.hidden = false;
    input.value = '';
    input.focus();

    const done = (t) => {
      modal.hidden = true;
      saveBtn.removeEventListener('click', onSave);
      input.removeEventListener('keydown', onKey);
      resolve(t);
    };

    const onSave = () => {
      const t = input.value.trim();
      if (t) {
        setToken(t);
        done(t);
      }
    };

    const onKey = (e) => {
      if (e.key === 'Enter') onSave();
    };

    saveBtn.addEventListener('click', onSave);
    input.addEventListener('keydown', onKey);
  });
}

// ─── API ───────────────────────────────────────────────────────────────────

async function api(path, options = {}) {
  const token = getToken();
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });

  if (res.status === 401 || res.status === 403) {
    setToken(null);
    window.dispatchEvent(new CustomEvent('auth-error'));
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Unauthorized');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `HTTP ${res.status}`);
  }

  const contentType = res.headers.get('Content-Type') || '';
  if (contentType.includes('application/json')) return res.json();
  return res.text();
}

async function apiWithRetry(path, options = {}) {
  let lastErr;
  for (let i = 0; i < RETRY_ATTEMPTS; i++) {
    try {
      return await api(path, options);
    } catch (e) {
      lastErr = e;
      if (i < RETRY_ATTEMPTS - 1) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      }
    }
  }
  throw lastErr;
}

// ─── UI state ─────────────────────────────────────────────────────────────

function setConnectionStatus(status) {
  const el = document.getElementById('connection-status');
  if (!el) return;
  el.classList.remove('connected', 'error', 'loading');
  el.title = status;
  if (status === 'connected') el.classList.add('connected');
  else if (status === 'error') el.classList.add('error');
  else el.classList.add('loading');
}

function setLastUpdate(ts) {
  const el = document.getElementById('last-update');
  if (!el) return;
  if (!ts) {
    el.textContent = '';
    return;
  }
  const d = new Date(ts);
  el.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatPnl(value) {
  if (value == null || value === '') return '—';
  const n = Number(value);
  const sign = n >= 0 ? '+' : '';
  return `${sign}$${n.toFixed(2)}`;
}

function renderPnl(elementId, value) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = formatPnl(value);
  el.classList.remove('positive', 'negative');
  if (value != null && value !== '') {
    const n = Number(value);
    el.classList.add(n >= 0 ? 'positive' : 'negative');
  }
}

function renderDashboard(data) {
  if (!data) return;
  renderPnl('total-pnl', data.total_pnl);
  renderPnl('daily-pnl', data.daily_pnl);
  setLastUpdate(data.ts);
}

function renderPositions(positions) {
  const container = document.getElementById('positions-list');
  if (!container) return;
  if (!positions || positions.length === 0) {
    container.innerHTML = '<div class="empty-state">No open positions</div>';
    return;
  }
  container.innerHTML = positions
    .map((p) => {
      const symbol = p.symbol || p.ticker || '—';
      const side = (p.side || p.position_side || '').toLowerCase();
      const qty = p.qty ?? p.quantity ?? '';
      const pnl = p.unrealized_pnl ?? p.pnl;
      const pnlClass = pnl != null ? (Number(pnl) >= 0 ? 'positive' : 'negative') : '';
      const pnlStr = pnl != null ? formatPnl(pnl) : '';
      return `
        <div class="position-item">
          <div>
            <span class="position-symbol">${escapeHtml(symbol)}</span>
            <span class="position-side">${escapeHtml(side)} ${qty}</span>
          </div>
          <span class="position-pnl ${pnlClass}">${pnlStr}</span>
        </div>
      `;
    })
    .join('');
}

function renderAlerts(alerts) {
  const container = document.getElementById('alerts-feed');
  if (!container) return;
  if (!alerts || alerts.length === 0) {
    container.innerHTML = '<div class="empty-state">No recent alerts</div>';
    return;
  }
  container.innerHTML = alerts
    .map((a) => {
      const time = a.timestamp || a.created_at || a.time || '';
      const msg = a.message || a.text || a.body || JSON.stringify(a);
      const timeStr = time ? new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
      return `
        <div class="alert-item">
          <span class="alert-time">${escapeHtml(timeStr)}</span>
          <div class="alert-message">${escapeHtml(String(msg).slice(0, 120))}</div>
        </div>
      `;
    })
    .join('');
}

function renderSystem(data) {
  const container = document.getElementById('system-status');
  if (!container) return;
  if (!data || data.error) {
    container.innerHTML = `<div class="empty-state">${data && data.error ? escapeHtml(data.error) : '—'}</div>`;
    return;
  }
  const uptimeSec = data.uptime_seconds ?? 0;
  const uptimeStr = uptimeSec >= 3600
    ? `${Math.floor(uptimeSec / 3600)}h ${Math.floor((uptimeSec % 3600) / 60)}m`
    : `${Math.floor(uptimeSec / 60)}m`;
  container.innerHTML = `
    <div class="system-row"><span class="system-label">Host</span><span>${escapeHtml(data.hostname || '—')}</span></div>
    <div class="system-row"><span class="system-label">CPU</span><span>${data.cpu_percent != null ? data.cpu_percent.toFixed(0) + '%' : '—'}</span></div>
    <div class="system-row"><span class="system-label">Memory</span><span>${data.memory_used_percent != null ? data.memory_used_percent.toFixed(0) + '%' : '—'}</span></div>
    <div class="system-row"><span class="system-label">Uptime</span><span>${uptimeStr}</span></div>
  `;
}

function escapeHtml(s) {
  if (s == null) return '';
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// ─── Data fetch & refresh ─────────────────────────────────────────────────

async function fetchDashboard() {
  const data = await apiWithRetry('/dashboard');
  renderDashboard(data);
  return data;
}

async function fetchPositions() {
  const data = await apiWithRetry('/positions');
  renderPositions(data.positions || []);
}

async function fetchAlerts() {
  const data = await apiWithRetry('/alerts?limit=20');
  renderAlerts(data.alerts || []);
}

async function fetchSystem() {
  try {
    const data = await api('/system');
    renderSystem(data);
  } catch {
    renderSystem({ error: 'Unavailable' });
  }
}

async function refreshAll() {
  const token = getToken();
  if (!token) return;

  setConnectionStatus('loading');
  try {
    await Promise.all([
      fetchDashboard(),
      fetchPositions(),
      fetchAlerts(),
      fetchSystem(),
    ]);
    setConnectionStatus('connected');
  } catch (err) {
    setConnectionStatus('error');
    console.error('Refresh failed:', err);
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshAll, REFRESH_INTERVAL_MS);
}

// ─── Emergency actions ─────────────────────────────────────────────────────

function confirm(title, message) {
  return new Promise((resolve) => {
    pendingConfirm = resolve;
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-modal').hidden = false;
  });
}

function confirmResolve(ok) {
  if (pendingConfirm) {
    pendingConfirm(ok);
    pendingConfirm = null;
  }
  document.getElementById('confirm-modal').hidden = true;
}

async function emergencyAction(action, label) {
  const ok = await confirm(`Emergency: ${label}`, `Are you sure you want to ${label.toLowerCase()}?`);
  if (!ok) return;

  const btn = document.getElementById(`btn-${action === 'kill_switch' ? 'kill' : action}`);
  if (btn) btn.disabled = true;
  try {
    await api('/emergency', {
      method: 'POST',
      body: JSON.stringify({ action, reason: `Mobile: ${label}` }),
    });
    await refreshAll();
  } catch (e) {
    console.error(e);
    alert(e.message || 'Request failed');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ─── Init & event listeners ───────────────────────────────────────────────

function bindEmergencyButtons() {
  document.getElementById('btn-pause')?.addEventListener('click', () => emergencyAction('pause', 'Pause'));
  document.getElementById('btn-resume')?.addEventListener('click', () => emergencyAction('resume', 'Resume'));
  document.getElementById('btn-kill')?.addEventListener('click', () => emergencyAction('kill_switch', 'Kill switch'));
}

function bindConfirmModal() {
  document.getElementById('confirm-cancel')?.addEventListener('click', () => confirmResolve(false));
  document.getElementById('confirm-ok')?.addEventListener('click', () => confirmResolve(true));
}

function bindAuthError() {
  window.addEventListener('auth-error', () => {
    setToken(null);
    ensureToken().then(() => refreshAll());
  });
}

function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('sw.js').catch((err) => console.warn('SW registration failed:', err));
}

async function init() {
  registerServiceWorker();
  bindEmergencyButtons();
  bindConfirmModal();
  bindAuthError();

  await ensureToken();
  await refreshAll();
  startAutoRefresh();
}

init().catch((err) => {
  console.error('Init failed:', err);
  setConnectionStatus('error');
});
