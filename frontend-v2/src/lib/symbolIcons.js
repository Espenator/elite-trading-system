/**
 * Symbol Icons – logo URL from Financial Modeling Prep API.
 * Set VITE_FMP_API_KEY in .env. Falls back to initials when key is missing or image fails.
 * Used by SymbolIcon component for OpenClaw candidates, positions, indices, etc.
 */

const FMP_IMAGE_BASE = "https://financialmodelingprep.com/image-stock";

/**
 * Returns the FMP logo image URL for a ticker.
 * Requires VITE_FMP_API_KEY in frontend-v2/.env (exposed by Vite).
 * @param {string} symbol - Ticker symbol (e.g. AMZN, AAPL)
 * @returns {string} - URL to try (e.g. .../image-stock/AAPL.png?apikey=...) or "" if no key
 */
export function getSymbolIconUrl(symbol) {
  if (!symbol || typeof symbol !== "string") return "";
  const key = symbol.trim().toUpperCase();
  const apiKey = import.meta.env?.VITE_FMP_API_KEY ?? "";
  if (!apiKey) return "";
  return `${FMP_IMAGE_BASE}/${key}.png?apikey=${encodeURIComponent(apiKey)}`;
}

/**
 * Returns 1–2 letter initials for a symbol when no icon is available.
 * @param {string} symbol - Ticker symbol
 * @param {number} [maxChars=2] - Max characters to use
 * @returns {string}
 */
export function getSymbolInitials(symbol, maxChars = 2) {
  if (!symbol || typeof symbol !== "string") return "?";
  const s = symbol.trim().toUpperCase();
  if (s.length <= maxChars) return s;
  return s.slice(0, maxChars);
}
