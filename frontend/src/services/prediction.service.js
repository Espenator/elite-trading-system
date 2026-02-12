/**
 * Prediction API: signals (ML) and backtest (research doc).
 * Base URL: same as backend API (e.g. http://localhost:8001/api/v1).
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export async function fetchSignals(asOf) {
  const params = asOf ? `?as_of=${asOf}` : '';
  const res = await fetch(`${API_BASE}/signals${params}`);
  if (!res.ok) throw new Error('Failed to fetch signals');
  return res.json();
}

export async function runBacktest({ start, end, modelId, nStocks = 20, minScore }) {
  const query = new URLSearchParams({ start, end, model_id: modelId, n_stocks: String(nStocks) });
  if (minScore != null) query.append('min_score', String(minScore));
  const res = await fetch(`${API_BASE}/backtest?${query.toString()}`);
  if (!res.ok) throw new Error('Backtest failed');
  return res.json();
}

export async function getDataStatus() {
  const res = await fetch(`${API_BASE}/status/data`);
  if (!res.ok) throw new Error('Failed to fetch data status');
  return res.json();
}

export default { fetchSignals, runBacktest, getDataStatus };
