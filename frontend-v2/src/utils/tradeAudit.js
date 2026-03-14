/**
 * Trade action audit trail — logs every trade attempt to localStorage.
 * Keeps last 100 entries for debugging and compliance.
 */
const STORAGE_KEY = 'embodier_trade_audit';
const MAX_ENTRIES = 100;

export function logTradeAction({ action, details, confirmed, result }) {
  try {
    const entries = getTradeAudit();
    entries.unshift({
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
      action,
      details: typeof details === 'string' ? details : JSON.stringify(details),
      confirmed: !!confirmed,
      result: result || 'pending',
    });
    if (entries.length > MAX_ENTRIES) entries.length = MAX_ENTRIES;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    console.log(`[TradeAudit] ${action}:`, { confirmed, details });
  } catch (err) {
    console.warn('[TradeAudit] Failed to log:', err);
  }
}

export function getTradeAudit() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

export function clearTradeAudit() {
  localStorage.removeItem(STORAGE_KEY);
}
