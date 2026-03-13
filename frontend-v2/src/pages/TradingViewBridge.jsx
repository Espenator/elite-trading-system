// TradingView Bridge — morning briefing, position monitor, webhook status, Pine Script
// Uses useApi for briefing, positions, config; copy-pasteable TradingView levels
import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getAuthHeaders } from '../config/api';
import { Copy, Download, ExternalLink, Tv, RefreshCw } from 'lucide-react';

const REGIME_EMOJI = { bull: '🟢', sideways: '🟡', bear: '🔴', crisis: '⚫' };
const REGIME_COLOR = {
  bull: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  sideways: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  bear: 'bg-red-500/20 text-red-400 border-red-500/30',
  crisis: 'bg-gray-800 text-gray-300 border-gray-600',
};

function formatLevelsForCopy(idea) {
  const sym = (idea.symbol || idea.ticker || '').toUpperCase();
  const dir = (idea.direction || idea.action || 'buy').toLowerCase();
  const entry = idea.entry_zone?.[0] ?? idea.entry ?? idea.price ?? '—';
  const stop = idea.stop_loss ?? idea.stop ?? '—';
  const t1 = idea.target_1 ?? idea.target1 ?? '—';
  const t2 = idea.target_2 ?? idea.target2 ?? '—';
  return `Symbol: ${sym}\nDirection: ${dir.toUpperCase()}\nEntry: ${entry}\nStop: ${stop}\nTarget 1: ${t1}\nTarget 2: ${t2}`;
}

export default function TradingViewBridge() {
  const navigate = useNavigate();
  const { data: briefing, loading: briefingLoading, error: briefingError, refetch: refetchBriefing } = useApi('morningBriefing', { pollIntervalMs: 60000 });
  const { data: positions, loading: positionsLoading } = useApi('briefingPositions', { pollIntervalMs: 60000 });
  const { data: tvConfig } = useApi('tradingviewConfig', { pollIntervalMs: 30000 });

  const [pushLoading, setPushLoading] = useState(false);
  const [pineScript, setPineScript] = useState(null);

  const regime = briefing?.regime ?? {};
  const regimeState = (regime.state || 'sideways').toLowerCase();
  const portfolio = briefing?.portfolio ?? {};
  const heatPct = Number(portfolio.heat_pct) || 0;
  const tradeIdeas = briefing?.trade_ideas ?? [];
  const positionsList = Array.isArray(positions) ? positions : (positions?.positions ?? positions?.data ?? []);

  const copyToClipboard = useCallback((text, label) => {
    if (!text) {
      toast.warning('Nothing to copy');
      return;
    }
    navigator.clipboard.writeText(text).then(
      () => toast.success(`${label} copied`),
      () => toast.error('Copy failed')
    );
  }, []);

  const copyAllLevels = useCallback(() => {
    const blocks = tradeIdeas.map((idea, i) => {
      const header = `--- ${(idea.symbol || idea.ticker || '').toUpperCase()} ---`;
      return `${header}\n${formatLevelsForCopy(idea)}`;
    });
    const full = blocks.join('\n\n');
    copyToClipboard(full, 'All levels');
  }, [tradeIdeas, copyToClipboard]);

  const handlePushWebhook = useCallback(async (execute = false) => {
    setPushLoading(true);
    try {
      // POST /api/v1/tradingview/push-signals — uses latest briefing trade_ideas when body empty; execute=false = monitoring only
      const url = `${getApiUrl('tradingviewPushSignals')}?execute=${execute}`;
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(tradeIdeas.length > 0 ? tradeIdeas : null),
      });
      const res = await r.json().catch(() => ({}));
      if (r.ok) {
        const sent = res?.sent ?? (res?.monitor_results?.length > 0);
        toast.success(sent ? (execute ? 'Pushed to TradersPost (execute)' : 'Pushed to webhook (monitor only)') : 'No webhook configured');
      } else {
        toast.error(res?.detail?.message ?? res?.detail ?? 'Push failed');
      }
    } catch (e) {
      toast.error(e?.message || 'Push failed');
    } finally {
      setPushLoading(false);
    }
  }, [tradeIdeas]);

  const handleDownloadPineScript = useCallback(async () => {
    try {
      const url = getApiUrl('tradingviewPineScript');
      const r = await fetch(url);
      const text = await r.text();
      if (!r.ok) throw new Error('Failed to fetch');
      const blob = new Blob([text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'embodier_signal_overlay.pine';
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success('Pine Script downloaded');
    } catch (e) {
      toast.error(e?.message || 'Download failed');
    }
  }, []);

  return (
    <div className="p-6 max-w-5xl">
      {/* Command strip / header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white flex items-center gap-2">
            <Tv className="w-5 h-5 text-cyan-400" />
            TradingView Bridge
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Morning briefing, position monitor, and outbound webhook for TradingView / TradersPost.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetchBriefing()}
          disabled={briefingLoading}
          className="px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 disabled:opacity-50 text-xs flex items-center gap-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${briefingLoading ? 'animate-spin' : ''}`} />
          Refresh Briefing
        </button>
      </div>

      {/* Regime + Portfolio strip */}
      <div className="flex flex-wrap items-center gap-4 mb-6 p-4 rounded-lg border border-white/10 bg-white/5">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Regime</span>
          <span className={`px-2 py-1 rounded border text-sm font-medium ${REGIME_COLOR[regimeState] || REGIME_COLOR.sideways}`}>
            {REGIME_EMOJI[regimeState] || '🟡'} {(regime.state || '—').toUpperCase()}
          </span>
          {regime.signal_threshold != null && (
            <span className="text-xs text-gray-500">Threshold: {regime.signal_threshold}</span>
          )}
        </div>
        <div className="flex-1 min-w-[200px]">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Portfolio heat</span>
            <span>{heatPct}%</span>
          </div>
          <div className="h-2 rounded-full bg-gray-700 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${heatPct > 8 ? 'bg-red-500' : heatPct > 6 ? 'bg-amber-500' : 'bg-cyan-500'}`}
              style={{ width: `${Math.min(100, heatPct)}%` }}
            />
          </div>
        </div>
        <div className="text-sm text-gray-400">
          Value: ${Number(portfolio.total_value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          {' · '}Positions: {portfolio.open_positions ?? 0}
        </div>
      </div>

      {/* Trade ideas */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Today&apos;s trade ideas</h2>
          <div className="flex gap-2">
            {tradeIdeas.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={copyAllLevels}
                  className="px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 text-xs flex items-center gap-2"
                >
                  <Copy className="w-3.5 h-3.5" /> Copy All Levels
                </button>
                    <button
                  type="button"
                  disabled={pushLoading}
                  onClick={() => handlePushWebhook(false)}
                  className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-50 text-xs flex items-center gap-2"
                  title="Send to monitoring webhook only (e.g. webhook.site)"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Push to Webhook
                </button>
                <button
                  type="button"
                  disabled={pushLoading}
                  onClick={() => handlePushWebhook(true)}
                  className="px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 disabled:opacity-50 text-xs flex items-center gap-2"
                  title="Also send to TradersPost for Alpaca execution (explicit opt-in)"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Push & Execute
                </button>
              </>
            )}
            <button
              type="button"
              onClick={handleDownloadPineScript}
              className="px-3 py-1.5 rounded-lg bg-slate-500/20 text-slate-300 border border-slate-500/30 hover:bg-slate-500/30 text-xs flex items-center gap-2"
            >
              <Download className="w-3.5 h-3.5" /> Download Pine Script
            </button>
          </div>
        </div>
        {briefingLoading && <p className="text-sm text-gray-400">Loading briefing…</p>}
        {briefingError && <p className="text-sm text-red-400">Failed to load briefing</p>}
        {!briefingLoading && !briefingError && tradeIdeas.length === 0 && (
          <p className="text-sm text-gray-400">No ideas above threshold. Try again after signals refresh.</p>
        )}
        {!briefingLoading && tradeIdeas.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {tradeIdeas.map((idea, i) => (
              <div
                key={`${idea.symbol || idea.ticker}-${i}`}
                className="rounded-lg border border-white/10 bg-white/5 p-4 cursor-pointer hover:border-cyan-500/30 transition-colors"
                onClick={() => navigate(`/symbol/${encodeURIComponent(idea.symbol || idea.ticker || '')}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/symbol/${encodeURIComponent(idea.symbol || idea.ticker || '')}`)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold text-cyan-400">{idea.symbol || idea.ticker}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${(idea.direction || idea.action || '').toLowerCase() === 'sell' ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                    {(idea.direction || idea.action || 'LONG').toUpperCase()}
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-400">
                  <span>Entry: {idea.entry_zone?.[0] ?? idea.entry ?? idea.price ?? '—'}</span>
                  <span>Stop: {idea.stop_loss ?? idea.stop ?? '—'}</span>
                  <span>T1: {idea.target_1 ?? idea.target1 ?? '—'}</span>
                  <span>T2: {idea.target_2 ?? idea.target2 ?? '—'}</span>
                </div>
                <div className="mt-2 flex justify-between items-center" onClick={(e) => e.stopPropagation()}>
                  <span className="text-xs text-gray-500">Score {(idea?.score ?? '—')} · {idea?.position_size_pct != null ? `${Number(idea.position_size_pct).toFixed(0)}%` : ''}</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(formatLevelsForCopy(idea), 'Levels')}
                    className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" /> Copy
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Position monitor */}
      <section className="mb-8">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Position monitor</h2>
        {positionsLoading && <p className="text-sm text-gray-400">Loading positions…</p>}
        {!positionsLoading && positionsList.length === 0 && (
          <p className="text-sm text-gray-400">No open positions.</p>
        )}
        {!positionsLoading && positionsList.length > 0 && (
          <div className="space-y-2">
            {positionsList.map((pos, i) => (
              <div
                key={`${pos.symbol}-${i}`}
                className={`rounded-lg border p-3 cursor-pointer hover:border-cyan-500/30 transition-colors ${pos.needs_attention ? 'border-amber-500/40 bg-amber-500/5' : 'border-white/10 bg-white/5'}`}
                onClick={() => pos.symbol && navigate(`/symbol/${encodeURIComponent(pos.symbol)}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && pos.symbol && navigate(`/symbol/${encodeURIComponent(pos.symbol)}`)}
              >
                <div className="flex justify-between items-start">
                  <span className="font-mono font-medium text-white">{pos.symbol}</span>
                  <span className="text-xs text-gray-400">{pos.direction} · {pos.days_held ?? 0}d</span>
                </div>
                <div className="mt-1 flex flex-wrap gap-4 text-xs">
                  <span>P&L: ${(Number(pos?.unrealized_pnl ?? 0) ?? 0).toFixed(2)}</span>
                  <span>R: {pos.r_multiple ?? '—'}</span>
                  <span>Stop: {pos.stop_loss ?? '—'}</span>
                  {pos.needs_attention && (
                    <span className="text-amber-400">{pos.attention_reason}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Webhook status */}
      <section>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Webhook status</h2>
        <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-gray-400">
          <p>Monitor URL: {tvConfig?.webhook_configured || tvConfig?.monitor_url_configured ? 'Configured' : 'Not set'}</p>
          <p>TradersPost: {tvConfig?.traderspost_configured ? 'Configured' : 'Not set'}</p>
          {tvConfig?.last_push_timestamp && (
            <p className="text-xs text-gray-500 mt-1">Last push: {tvConfig.last_push_timestamp}</p>
          )}
        </div>
      </section>
    </div>
  );
}
