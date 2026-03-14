// =============================================================================
// RiskIntelligence.jsx — Embodier Trader
// Route: /risk | Section: Execution | Page 10
// Rebuilt to match mockup 13-risk-intelligence.png
// =============================================================================
import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from "../hooks/useApi";
import { useRiskScore, useDrawdownCheck, useKellyRanked } from "../hooks/useApi";
import { useSettings } from "../hooks/useSettings";
import { getApiUrl, getAuthHeaders, WS_CHANNELS } from "../config/api";
import ws from "../services/websocket";
import log from "@/utils/logger";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import {
  Shield, RefreshCw, Target, Grid3X3, Gauge, Brain, DollarSign,
  Clock, Octagon, ChevronDown, Radio, X
} from 'lucide-react';
import { ParameterSweepsPanel } from '../components/dashboard/RiskWidgets';
import SectionErrorBoundary from '../components/ui/SectionErrorBoundary';

// ─── COLOR PALETTE (dark theme) ─────────────────────────────────────────────
const C = {
  bg:        '#0B0E14',
  surface:   '#111827',
  card:      '#1A1F2E',
  border:    '#1E293B',
  cyan:      '#00D9FF',
  green:     '#10B981',
  red:       '#EF4444',
  amber:     '#F59E0B',
  purple:    '#A855F7',
  teal:      '#14B8A6',
  text:      '#f8fafc',
  muted:     '#64748B',
  dimText:   '#94A3B8',
};

// ─── RISK GRADE HELPER ──────────────────────────────────────────────────────
function gradeFromScore(score) {
  if (score <= 20) return { letter: 'A+', color: C.green };
  if (score <= 35) return { letter: 'A', color: C.green };
  if (score <= 50) return { letter: 'B', color: C.cyan };
  if (score <= 65) return { letter: 'C', color: C.amber };
  if (score <= 80) return { letter: 'D', color: C.red };
  return { letter: 'F', color: C.red };
}

function statusColor(status) {
  if (status === 'SAFE' || status === 'OK' || status === 'PASS') return C.green;
  if (status === 'WARNING' || status === 'CAUTION') return C.amber;
  return C.red;
}

// ─── SKELETON (no mock numbers) ──────────────────────────────────────────────
function Skeleton({ className = '', style = {} }) {
  return (
    <div
      className={`animate-pulse rounded bg-[rgba(42,52,68,0.6)] ${className}`}
      style={{ minHeight: 16, ...style }}
    />
  );
}

// ─── CORRELATION COLOR ──────────────────────────────────────────────────────
function corrCellBg(val) {
  const v = Math.abs(val ?? 0);
  if (v >= 0.8) return 'rgba(239,68,68,0.35)';
  if (v >= 0.6) return 'rgba(245,158,11,0.30)';
  if (v >= 0.4) return 'rgba(251,191,36,0.25)';
  if (v >= 0.2) return 'rgba(16,185,129,0.25)';
  return 'rgba(20,184,166,0.20)';
}

// ─── SAFETY CHECK ROW ───────────────────────────────────────────────────────
function SafetyCheck({ label, status }) {
  const passed = status === 'PASS' || status === 'OK' || status === 'SAFE';
  return (
    <div className="flex items-center justify-between py-1 border-b border-[rgba(42,52,68,0.5)] last:border-0">
      <span className="text-xs text-slate-300">{label}</span>
      <span className="text-xs font-mono font-bold" style={{ color: passed ? C.green : C.red }}>
        {passed ? '+ PASS' : 'x FAIL'}
      </span>
    </div>
  );
}

// ─── CORRELATION HEATMAP (API data only; click → drill-down) ─────────────────
function CorrelationHeatmap({ data, loading, onCellClick }) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-8 space-y-2">
        <Skeleton className="w-32 h-4" />
        <Skeleton className="w-48 h-24" />
      </div>
    );
  }
  if (!data || !data.symbols || !data.matrix || data.symbols.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 py-8">
        <Grid3X3 className="w-6 h-6 mb-2 opacity-40" />
        <div className="text-xs font-mono">No active positions for correlation analysis</div>
      </div>
    );
  }
  const { symbols, matrix } = data;
  const n = symbols.length;
  const cellSize = n > 8 ? 28 : 34;

  return (
    <div className="overflow-auto custom-scrollbar">
      <table className="border-collapse text-[10px] font-mono" style={{ minWidth: n * cellSize + 40 }}>
        <thead>
          <tr>
            <th className="py-1 px-1 text-left text-gray-500 sticky left-0 bg-[#111827] z-10"
                style={{ minWidth: 40 }}></th>
            {symbols.map((s) => (
              <th key={s} className="py-1 px-0.5 text-center font-bold text-[#00D9FF]"
                  style={{ minWidth: cellSize, fontSize: n > 8 ? '8px' : '9px' }}>
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((rowSym, ri) => (
            <tr key={rowSym}>
              <td className="py-0.5 px-1 font-bold sticky left-0 bg-[#111827] z-10 whitespace-nowrap text-[#00D9FF]"
                  style={{ fontSize: n > 8 ? '8px' : '9px' }}>
                {rowSym}
              </td>
              {matrix[ri]?.map((val, ci) => {
                const isDiag = ri === ci;
                const safeVal = val ?? 0;
                return (
                  <td
                    key={ci}
                    role={onCellClick && !isDiag ? 'button' : undefined}
                    onClick={onCellClick && !isDiag ? () => onCellClick(rowSym, symbols[ci], safeVal) : undefined}
                    className={`text-center font-bold transition-all ${onCellClick && !isDiag ? 'cursor-pointer hover:ring-1 hover:ring-cyan-500/50' : ''}`}
                    style={{
                      color: isDiag ? C.dimText : '#fff',
                      backgroundColor: isDiag ? 'rgba(0,217,255,0.08)' : corrCellBg(safeVal),
                      border: '1px solid rgba(42,52,68,0.3)',
                      fontSize: n > 8 ? '8px' : '9px',
                      padding: '3px 2px',
                      minWidth: cellSize,
                      height: cellSize,
                    }}
                    title={onCellClick && !isDiag ? `Click: ${rowSym} vs ${symbols[ci]} drill-down` : `${rowSym} vs ${symbols[ci]}: ${safeVal.toFixed(4)}`}
                  >
                    {isDiag ? '1.00' : safeVal.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── POSITION SIZER (API data only; no fake numbers) ─────────────────────────
function PositionSizer({ kelly, portfolioValue, loading }) {
  if (loading || !kelly) {
    return (
      <div className="space-y-2">
        <Skeleton className="w-full h-20" />
        <div className="flex justify-between gap-1.5">
          {['Full', 'Half', '1/4', 'Rec', 'Max', 'Min'].map((l) => (
            <Skeleton key={l} className="flex-1 h-3" />
          ))}
        </div>
      </div>
    );
  }
  const fullKellyPct = (typeof kelly.full_kelly === 'number' ? kelly.full_kelly : 0) * 100;
  const recPct = typeof kelly.recommended_pct === 'number' ? kelly.recommended_pct : (fullKellyPct * 0.25);
  const sizingBars = [
    { label: 'Full', pct: fullKellyPct, color: C.red },
    { label: 'Half', pct: fullKellyPct * 0.5, color: C.amber },
    { label: '1/4', pct: fullKellyPct * 0.25, color: C.green },
    { label: 'Rec', pct: recPct, color: C.cyan },
    { label: 'Max', pct: fullKellyPct * 0.75, color: C.purple },
    { label: 'Min', pct: fullKellyPct * 0.1, color: C.teal },
  ].map((b) => ({ ...b, pct: Math.max(0, b.pct) }));
  const maxPct = Math.max(...sizingBars.map((b) => b.pct), 0.01);

  return (
    <div>
      <div className="flex items-end justify-between gap-1.5" style={{ height: 100 }}>
        {sizingBars.map((bar, i) => {
          const h = Math.max((bar.pct / maxPct) * 100, 2);
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-[8px] font-mono font-bold" style={{ color: bar.color }}>
                {bar.pct.toFixed(1)}%
              </span>
              <div className="w-full bg-[#0B0E14] rounded-t relative" style={{ height: 80 }}>
                <div
                  className="absolute bottom-0 left-0 right-0 rounded-t transition-all duration-500"
                  style={{ height: `${h}%`, backgroundColor: bar.color, opacity: 0.85 }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between gap-1.5 mt-1">
        {sizingBars.map((bar, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-[8px] text-gray-500 font-mono">{bar.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================
export default function RiskIntelligence() {
  const navigate = useNavigate();
  const [timeframe, setTimeframe] = useState('1D');
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [riskModel, setRiskModel] = useState('Adaptive Multi-Factor');
  const [strategy, setStrategy] = useState('Enhanced MetaResolved TrenchRunner');
  const [emergencyCountdown, setEmergencyCountdown] = useState(null);
  const [sweepModalOpen, setSweepModalOpen] = useState(false);
  const [sweepParams, setSweepParams] = useState(null);
  const [correlationDrill, setCorrelationDrill] = useState(null);
  const [historyDayDetail, setHistoryDayDetail] = useState(null);
  const [stressResult, setStressResult] = useState(null);
  const [stressLoading, setStressLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const emergencyTimerRef = useRef(null);
  const emergencyAbortRef = useRef(null);

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // ─── RISK HOOKS (spec: useRiskScore, useDrawdownCheck, useKellyRanked) ──────
  const { data: riskScoreData, loading: riskScoreLoading } = useRiskScore(30000);
  const { data: drawdownData, loading: drawdownLoading } = useDrawdownCheck(30000);
  const { data: kellyRankedData } = useKellyRanked(true);
  const { settings, updateField, saveCategory, loading: settingsLoading } = useSettings();

  // ─── API HOOKS ────────────────────────────────────────────────────────────
  const { data: riskData, refetch: refetchRisk } = useApi('risk');
  const { data: shieldData, refetch: refetchShield } = useApi('riskShield');
  const { data: gaugesData, refetch: refetchGauges } = useApi('risk', { endpoint: '/risk/risk-gauges' });
  const { data: kellyData, loading: kellyLoading } = useApi('kellySizer');
  const { data: monteData } = useApi('risk', { endpoint: '/risk/monte-carlo' });
  const { data: historyData } = useApi('risk', { endpoint: '/risk/history' });
  const { data: portfolioData } = useApi('portfolio');
  const { data: correlationData, loading: correlationLoading } = useApi('risk', { endpoint: '/risk/correlation-matrix' });
  const { data: sweepStatusData } = useApi('swarmSweepStatus');
  const { data: regimeData } = useApi('risk', { endpoint: '/openclaw/regime' });

  const handleRefresh = useCallback(() => {
    setLastRefresh(new Date());
    refetchRisk(); refetchShield(); refetchGauges();
  }, [refetchRisk, refetchShield, refetchGauges]);

  // ─── WebSocket live updates ──────────────────────────────────────────────
  useEffect(() => {
    const unsub = ws.on(WS_CHANNELS.risk, () => handleRefresh());
    return unsub;
  }, [handleRefresh]);

  // ─── DERIVED VALUES (API only; no fake numbers; null → skeleton) ───────────
  const rawScore = riskScoreData?.score ?? riskData?.risk_score;
  const riskScore = (typeof rawScore === 'number' && !Number.isNaN(rawScore)) ? rawScore : null;
  const grade = riskScore != null ? gradeFromScore(riskScore) : null;
  const systemStatus = riskData?.system_status
    ?? (riskScore != null ? (riskScore <= 35 ? 'SAFE' : riskScore <= 65 ? 'CAUTION' : 'DANGER') : null);

  const shieldLoading = !shieldData && riskData === undefined;
  const safetyChecks = shieldData?.checks ?? [];

  const gaugesLoading = !gaugesData;
  const rawGauges = gaugesData?.gauges ?? [];

  const kelly = kellyData ?? null;
  const monte = monteData ?? null;

  const configItems = useMemo(() => {
    if (!riskData) return [];
    return [
      { label: 'Signal Confidence Sentinel', value: riskData.signal_confidence, color: C.green },
      { label: 'Capital Exposure Watchdog', value: riskData.capital_exposure, color: C.amber },
      { label: 'Regime Sentinels', value: riskData.regime_sentinel, color: C.cyan },
      { label: 'Volatility Monitor', value: riskData.vol_monitor, color: C.cyan },
      { label: 'Drawdown Protection', value: riskData.dd_protection, color: C.green },
      { label: 'Multi-Agent Consensus', value: riskData.consensus, color: C.cyan },
      { label: 'Performance Analytics', value: riskData.perf_analytics, color: C.green },
      { label: 'Risk Budgets', value: riskData.risk_budgets, color: C.cyan },
    ].filter((i) => i.value != null);
  }, [riskData]);

  const volRegimeItems = useMemo(() => {
    if (!riskData) return [];
    const items = [
      { label: 'VIX Level', value: riskData.vix_current, max: 80, color: C.amber },
      { label: 'Hist Vol (20d)', value: riskData.hist_vol_20d, max: 60, color: C.cyan },
      { label: 'Impl Vol Skew', value: riskData.iv_skew, max: 20, color: C.purple },
      { label: 'Vol Regime', value: riskData.vol_regime_score, max: 100, color: C.green },
    ];
    return items.filter((i) => typeof i.value === 'number');
  }, [riskData]);

  const safeNum = (v) => (typeof v === 'number' && !Number.isNaN(v) ? v : null);
  const agentMonitors = useMemo(() => {
    if (!monte && !kelly) return [];
    return [
      { label: 'Monte Carlo P(profit)', value: safeNum(monte?.prob_profit) != null ? Math.min(safeNum(monte.prob_profit) * 100, 100) : null, color: C.green },
      { label: 'MC Median Return', value: safeNum(monte?.median_return) != null ? Math.max(0, safeNum(monte.median_return) * 100 + 50) : null, color: C.cyan },
      { label: 'Ruin Probability', value: safeNum(monte?.ruin_probability) != null ? Math.min(safeNum(monte.ruin_probability) * 1000, 100) : null, color: C.red },
      { label: 'Max DD (P95)', value: safeNum(monte?.max_dd_p95) != null ? Math.min(Math.abs(safeNum(monte.max_dd_p95)) * 300, 100) : null, color: C.amber },
      { label: 'Kelly Edge', value: safeNum(kelly?.edge) != null ? Math.min(safeNum(kelly.edge) * 100, 100) : null, color: C.purple },
      { label: 'Win Rate', value: safeNum(kelly?.win_rate) != null ? safeNum(kelly.win_rate) * 100 : null, color: C.green },
    ].filter((i) => i.value != null);
  }, [monte, kelly]);

  // 90-day risk history — show only real API data, no fabricated fallback
  const history = historyData?.history ?? [];
  const historyTableRows = useMemo(() => {
    if (history.length > 0) return history.slice(-20);
    // No real data — return empty array (table shows zero-state)
    return [];
  }, [history]);

  // Portfolio value for sizer
  const portfolioValue = portfolioData?.total_value ?? portfolioData?.portfolio_value ?? riskData?.portfolio_value ?? 0;

  // ─── EMERGENCY STOP: 3s countdown then POST /orders/emergency-stop ─────────
  useEffect(() => {
    return () => {
      if (emergencyTimerRef.current) clearInterval(emergencyTimerRef.current);
    };
  }, []);

  const handleEmergencyStopClick = useCallback(() => {
    setEmergencyCountdown(3);
  }, []);

  useEffect(() => {
    if (emergencyCountdown == null) return;
    if (emergencyCountdown <= 0) {
      const ctrl = new AbortController();
      emergencyAbortRef.current = ctrl;
      const timeout = setTimeout(() => ctrl.abort(), 10000);
      (async () => {
        try {
          const res = await fetch(getApiUrl('orders/emergency-stop'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            signal: ctrl.signal,
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          showToast('Emergency stop executed', 'success');
          handleRefresh();
        } catch (err) {
          if (err.name !== 'AbortError') {
            log.error('Emergency stop failed:', err);
            showToast(`Emergency stop failed: ${err.message}`, 'error');
          }
        } finally {
          clearTimeout(timeout);
          emergencyAbortRef.current = null;
          setEmergencyCountdown(null);
        }
      })();
      return;
    }
    const t = setInterval(() => setEmergencyCountdown((c) => c - 1), 1000);
    emergencyTimerRef.current = t;
    return () => clearInterval(t);
  }, [emergencyCountdown]);

  const cancelEmergencyCountdown = useCallback(() => {
    if (emergencyTimerRef.current) {
      clearInterval(emergencyTimerRef.current);
      emergencyTimerRef.current = null;
    }
    if (emergencyAbortRef.current) {
      emergencyAbortRef.current.abort();
      emergencyAbortRef.current = null;
    }
    setEmergencyCountdown(null);
  }, []);

  // Backend risk.py supports: halt, resume, flatten. Map UI actions to these.
  const handleOtherEmergency = async (action) => {
    const actionMap = { HEDGE: 'halt', REDUCE: 'flatten', FREEZE: 'halt' };
    const backendAction = actionMap[action] || action.toLowerCase();
    try {
      const res = await fetch(`${getApiUrl('risk')}/emergency/${backendAction}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        log.error(`Emergency ${action} failed:`, res.status, data?.detail ?? data);
        showToast(`${action} failed: ${data?.detail ?? `HTTP ${res.status}`}`, 'error');
        return;
      }
      showToast(`${action} executed successfully`, 'success');
      handleRefresh();
    } catch (err) {
      log.error(`Emergency ${action} failed:`, err);
      showToast(`${action} failed: ${err.message}`, 'error');
    }
  };

  const handleRunSweepClick = useCallback((values) => {
    setSweepParams(values);
    setSweepModalOpen(true);
  }, []);

  const handleRunSweepConfirm = useCallback(async () => {
    setSweepModalOpen(false);
    const values = sweepParams;
    setSweepParams(null);
    try {
      const res = await fetch(getApiUrl('swarmSweepStatus'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody?.detail ?? `HTTP ${res.status}: ${res.statusText}`);
      }
      showToast('Parameter sweep started', 'success');
      handleRefresh();
    } catch (err) {
      log.error('Sweep start failed:', err);
      showToast(`Sweep failed: ${err.message}`, 'error');
    }
  }, [sweepParams, showToast]);

  const runStressTest = useCallback(async () => {
    setStressLoading(true);
    setStressResult(null);
    try {
      const res = await fetch(getApiUrl('risk/stress-test'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        setStressResult({ error: errBody?.detail ?? `HTTP ${res.status}: ${res.statusText}` });
        showToast('Stress test failed', 'error');
        return;
      }
      const data = await res.json();
      setStressResult(data);
      showToast('Stress test complete', 'success');
    } catch (err) {
      log.error('Stress test failed:', err);
      setStressResult({ error: String(err?.message ?? err) });
      showToast(`Stress test error: ${err.message}`, 'error');
    } finally {
      setStressLoading(false);
    }
  }, [showToast]);

  const riskParams = settings?.risk ?? null;
  const handleRiskParamChange = useCallback((paramKey, value) => {
    updateField('risk', paramKey, value);
  }, [updateField]);
  const [savingRisk, setSavingRisk] = useState(false);
  const handleSaveRiskSettings = useCallback(async () => {
    setSavingRisk(true);
    try {
      await saveCategory('risk');
      showToast('Risk settings saved', 'success');
    } catch (err) {
      showToast(`Failed to save: ${err.message}`, 'error');
    } finally {
      setSavingRisk(false);
    }
  }, [saveCategory, showToast]);

  // =========================================================================
  // RENDER
  // =========================================================================
  return (
    <div className="flex flex-col min-h-0" style={{ backgroundColor: C.bg, color: C.text }}>

      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-[60] px-4 py-2 rounded-lg shadow-lg text-sm font-mono border backdrop-blur-sm transition-all ${
          toast.type === 'success' ? 'bg-green-900/80 border-green-500/50 text-green-300' :
          toast.type === 'error' ? 'bg-red-900/80 border-red-500/50 text-red-300' :
          'bg-slate-800/80 border-slate-500/50 text-slate-300'
        }`}>
          {toast.msg}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════
          HEADER BAR (mockup 13-risk-intelligence: aligns with system header style)
          ════════════════════════════════════════════════════════════════════════ */}
      <header className="px-5 py-3 flex items-center justify-between border-b border-[rgba(42,52,68,0.5)] shrink-0 bg-[#111827]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center"
               style={{ backgroundColor: (grade?.color ?? C.muted) + '20' }}>
            <Shield className="w-5 h-5" style={{ color: grade?.color ?? C.muted }} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Risk Intelligence
              <Badge variant="primary" size="sm">LIVE</Badge>
            </h1>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-mono">
              Shield Protection &middot; Real-Time Monitoring
            </span>
          </div>
        </div>

        {/* Center: Grade + Score + Status (skeleton when loading) */}
        <div className="flex items-center gap-6">
          <div className="text-center min-w-[4rem]">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Grade</div>
            {riskScoreLoading || grade == null ? (
              <Skeleton className="h-9 w-12 mx-auto mt-0.5" />
            ) : (
              <div className="text-3xl font-black font-mono leading-none" style={{ color: grade.color }}>
                {grade.letter}
              </div>
            )}
          </div>
          <div className="text-center min-w-[4rem]">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Risk Score</div>
            {riskScoreLoading || riskScore == null ? (
              <Skeleton className="h-8 w-10 mx-auto mt-0.5" />
            ) : (
              <div className="text-2xl font-bold font-mono leading-none" style={{ color: grade?.color }}>
                {riskScore}
              </div>
            )}
          </div>
          <div className="text-center min-w-[4rem]">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Status</div>
            {!riskData && !shieldData ? (
              <Skeleton className="h-4 w-16 mx-auto mt-0.5" />
            ) : (
              <div className="text-sm font-bold font-mono" style={{ color: systemStatus != null ? statusColor(systemStatus) : C.muted }}>
                {systemStatus ?? '—'}
              </div>
            )}
          </div>
        </div>

        {/* Right: timeframe + refresh */}
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg overflow-hidden border border-[rgba(42,52,68,0.5)]">
            {['1D', '1W', '1M', '3M'].map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-xs font-mono font-bold transition-all
                  ${timeframe === tf
                    ? 'bg-cyan-500/20 text-[#00D9FF]'
                    : 'bg-[#1A1F2E] text-gray-500 hover:text-slate-300'}`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-white/5 border border-[rgba(42,52,68,0.5)]
                       hover:border-[#00D9FF]/50 text-gray-500 hover:text-[#00D9FF] transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <span className="text-[10px] text-gray-500 font-mono">
            {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* ─── Emergency stop countdown modal ──────────────────────────────────── */}
      {emergencyCountdown != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
             onKeyDown={(e) => { if (e.key === 'Escape') cancelEmergencyCountdown(); }}
             tabIndex={-1}
             ref={(el) => el?.focus()}>
          <div className="bg-[#111827] border border-red-500/50 rounded-xl p-6 max-w-sm shadow-xl text-center">
            <div className="text-red-400 font-bold text-lg mb-2">Flattening all positions</div>
            <div className="text-4xl font-mono font-black text-white mb-4">
              {emergencyCountdown > 0 ? emergencyCountdown : '…'}
            </div>
            <p className="text-xs text-gray-400 mb-4">
              {emergencyCountdown > 0 ? 'POST /orders/emergency-stop in ' + emergencyCountdown + 's' : 'Executing…'}
            </p>
            <button
              onClick={cancelEmergencyCountdown}
              className="px-4 py-2 rounded-lg bg-slate-600 hover:bg-slate-500 text-white text-sm font-mono"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════
          MAIN CONTENT
          ════════════════════════════════════════════════════════════════════════ */}
      <div className="p-3 space-y-3">
      {/* TOP SECTION ROW: Risk Configuration | Parameter Sweeps | Realtime Risk Detail */}
      <SectionErrorBoundary name="Risk Configuration">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">

        {/* --- Risk Configuration (left, 4 cols) --- */}
        <Card title="Risk Configuration"
              subtitle={`Strategy: ${strategy}`}
              className="col-span-1 md:col-span-4"
              action={<Badge variant="success" size="sm">ACTIVE</Badge>}>
          <div className="space-y-3">
            {/* Risk Model Selector */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">Risk Model</label>
              <div className="relative">
                <select
                  value={riskModel}
                  onChange={(e) => setRiskModel(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-lg px-3 py-1.5 text-xs text-white
                             font-mono appearance-none cursor-pointer hover:border-[#00D9FF]/50 transition-all"
                >
                  <option>Adaptive Multi-Factor</option>
                  <option>Momentum Risk</option>
                  <option>Mean Reversion</option>
                  <option>Volatility Regime</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
              </div>
            </div>
            {/* Strategy Selector */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">Strategy</label>
              <div className="relative">
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-lg px-3 py-1.5 text-xs text-white
                             font-mono appearance-none cursor-pointer hover:border-[#00D9FF]/50 transition-all"
                >
                  <option>Enhanced MetaResolved TrenchRunner</option>
                  <option>Momentum Alpha</option>
                  <option>Multi-Agent Consensus</option>
                  <option>Hybrid Adaptive</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
              </div>
            </div>
            {/* Risk params from useSettings (persist via updateField + saveCategory) */}
            {riskParams && (
              <div className="space-y-2 pt-2 border-t border-[rgba(42,52,68,0.5)]">
                {[
                  { key: 'maxDrawdownLimit', altKey: 'maxDailyDrawdown', label: 'Max drawdown %', min: 0.02, max: 0.25, step: 0.01, fmt: (v) => `${(v * 100).toFixed(0)}%` },
                  { key: 'positionSizePct', altKey: 'positionSizeLimit', label: 'Position size %', min: 0.5, max: 10, step: 0.5, fmt: (v) => `${v}%` },
                  { key: 'maxDailyLossPct', altKey: null, label: 'Max daily loss %', min: 1, max: 10, step: 0.5, fmt: (v) => `${v}%` },
                ].map(({ key, altKey, label, min, max, step, fmt }) => {
                  const val = riskParams[key] ?? (altKey ? riskParams[altKey] : undefined);
                  if (val == null) return null;
                  const num = Number(val);
                  return (
                    <div key={key} className="flex items-center justify-between gap-2">
                      <span className="text-[10px] text-gray-400 truncate">{label}</span>
                      <input
                        type="range"
                        min={min}
                        max={max}
                        step={step}
                        value={num}
                        onChange={(e) => handleRiskParamChange(key, Number(e.target.value))}
                        className="flex-1 h-1.5 rounded bg-[#0B0E14] accent-cyan-500"
                      />
                      <span className="text-[10px] font-mono text-[#00D9FF] w-10 text-right">{fmt(num)}</span>
                    </div>
                  );
                })}
                <button
                  onClick={handleSaveRiskSettings}
                  disabled={savingRisk}
                  className="w-full py-1.5 rounded text-[10px] font-bold uppercase bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500/30 disabled:opacity-50"
                >
                  {savingRisk ? 'Saving…' : 'Save risk settings'}
                </button>
              </div>
            )}
            {settingsLoading && !riskParams && <Skeleton className="h-20 w-full" />}
            {/* Config toggles (API only) */}
            <div className="space-y-1 pt-1">
              {configItems.length === 0 && riskData && <div className="text-[10px] text-gray-500">No config items</div>}
              {configItems.length === 0 && !riskData && <Skeleton className="h-16 w-full" />}
              {configItems.map((item, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-[rgba(42,52,68,0.5)]/60 last:border-0">
                  <span className="text-xs text-gray-400">{item.label}</span>
                  <span className="text-xs font-mono font-bold" style={{ color: item.color }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* --- Parameter Sweeps (center, 5 cols) --- */}
        <Card title="Parameter Sweeps" className="col-span-1 md:col-span-5"
              action={<span className="text-[10px] text-gray-500 font-mono">{timeframe}</span>}>
          <ParameterSweepsPanel
            onRun={handleRunSweepClick}
            onStop={() => {}}
          />
          {sweepModalOpen && sweepParams && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
              <div className="bg-[#111827] border border-cyan-500/40 rounded-xl p-4 max-w-sm w-full mx-2">
                <div className="text-cyan-400 font-bold text-sm mb-2">Run parameter sweep</div>
                <pre className="text-[10px] font-mono text-gray-400 mb-4 overflow-auto max-h-32">
                  {JSON.stringify(sweepParams, null, 2)}
                </pre>
                <div className="flex gap-2">
                  <button onClick={() => { setSweepModalOpen(false); setSweepParams(null); }} className="flex-1 py-2 rounded bg-slate-600 text-white text-xs font-mono">Cancel</button>
                  <button onClick={handleRunSweepConfirm} className="flex-1 py-2 rounded bg-cyan-600 text-white text-xs font-mono">Run sweep</button>
                </div>
              </div>
            </div>
          )}
          {/* Sweep results from API or empty state */}
          <div className="overflow-auto custom-scrollbar mt-2">
            {sweepStatusData ? (
              <div className="text-[10px] font-mono text-gray-400 py-2">
                {sweepStatusData.running ? 'Sweep running…' : 'Sweep idle. Run above to start.'}
              </div>
            ) : (
              <div className="text-[10px] font-mono text-gray-500 py-2">No sweep data</div>
            )}
          </div>
        </Card>

        {/* --- RealTime Risk Vitals (right, 3 cols) --- */}
        <Card title="RealTime Risk Vitals" className="col-span-1 md:col-span-3"
              action={<Badge variant={systemStatus === 'SAFE' ? 'success' : 'warning'} size="sm">{systemStatus ?? '—'}</Badge>}>
          <div className="space-y-2.5">
            {gaugesLoading ? (
              <>
                <Skeleton className="w-full h-6" />
                <Skeleton className="w-full h-6" />
                <Skeleton className="w-full h-6" />
              </>
            ) : rawGauges.length === 0 ? (
              <div className="text-[10px] text-gray-500 py-2">No gauge data</div>
            ) : (
              [
                { label: 'Portfolio VaR (95%)', key: 'VaR 95%', color: C.amber },
                { label: 'Tail Risk (CVaR)', key: 'CVaR 95%', color: C.red },
                { label: 'Portfolio Heat', key: 'Portfolio Heat', color: C.purple },
                { label: 'Tail Risk', key: 'Tail Risk', color: C.cyan },
                { label: 'Delta Exposure', key: 'Delta', color: C.amber },
                { label: 'Gamma Exposure', key: 'Gamma', color: C.green },
                { label: 'Vega Exposure', key: 'Vega', color: C.teal },
              ].map((item, i) => {
                const gauge = rawGauges.find((g) => (g.name || g.label) === item.key);
                const val = gauge?.value;
                const max = gauge?.max || 100;
                const unit = gauge?.unit || '%';
                const num = typeof val === 'number' ? val : null;
                const pct = num != null && max > 0 ? Math.min((num / max) * 100, 100) : 0;
                return (
                  <div key={i} className="space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-gray-400">{item.label}</span>
                      <span className="text-[10px] font-mono font-bold" style={{ color: item.color }}>
                        {num != null ? `${unit === '$' ? '$' : ''}${num.toLocaleString()}${unit === '%' ? '%' : ''}` : '—'}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-[#0B0E14] rounded-full overflow-hidden">
                      {num != null && (
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.max(pct, 2)}%`,
                            backgroundColor: item.color,
                            boxShadow: `0 0 6px ${item.color}40`,
                          }}
                        />
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>
      </div>
      </SectionErrorBoundary>

      {/* ════════════════════════════════════════════════════════════════════════
          MAIN GRID ROW: Stop-Loss | Correlation | Vol Regime | AI Monitors | Position Sizing
          ════════════════════════════════════════════════════════════════════════ */}
      <SectionErrorBoundary name="Risk Monitors">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-12 gap-3">

        {/* --- Stop-Loss Command (2 cols) --- */}
        <Card title="Stop-Loss Command" className="col-span-1 md:col-span-2"
              action={
                safetyChecks.length > 0 ? (
                  <span className="text-[10px] font-mono" style={{ color: safetyChecks.every(c => c.status === 'PASS') ? C.green : C.amber }}>
                    {safetyChecks.filter(c => c.status === 'PASS').length}/{safetyChecks.length} PASS
                  </span>
                ) : (
                  <span className="text-[10px] font-mono text-gray-500">—</span>
                )
              }>
          <div className="space-y-0.5 mb-3">
            {shieldLoading ? (
              <>
                <Skeleton className="w-full h-5" />
                <Skeleton className="w-full h-5" />
                <Skeleton className="w-full h-5" />
              </>
            ) : safetyChecks.length === 0 ? (
              <div className="text-[10px] text-gray-500">No safety checks data</div>
            ) : (
              safetyChecks.map((check, i) => (
                <SafetyCheck key={i} label={check.label} status={check.status} />
              ))
            )}
          </div>

          {/* Emergency Actions: 3s countdown then POST /orders/emergency-stop */}
          <div className="border-t border-[rgba(42,52,68,0.5)] pt-3 space-y-2">
            <button
              onClick={handleEmergencyStopClick}
              disabled={emergencyCountdown != null}
              className="w-full py-2.5 rounded-lg text-xs font-bold uppercase
                         bg-red-600 hover:bg-red-500 text-white
                         border-2 border-red-400 shadow-lg shadow-red-500/20
                         transition-all active:scale-95 flex items-center justify-center gap-2 disabled:opacity-70"
            >
              <Octagon className="w-4 h-4" />
              EMERGENCY STOP ALL
            </button>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                onClick={() => handleOtherEmergency('HEDGE')}
                className="py-1.5 rounded-lg text-[10px] font-bold uppercase
                           bg-purple-600/30 hover:bg-purple-600/50 text-purple-300
                           border border-purple-500/30 transition-all"
              >
                Hedge
              </button>
              <button
                onClick={() => handleOtherEmergency('REDUCE')}
                className="py-1.5 rounded-lg text-[10px] font-bold uppercase
                           bg-amber-600/30 hover:bg-amber-600/50 text-amber-300
                           border border-amber-500/30 transition-all"
              >
                Reduce
              </button>
              <button
                onClick={() => handleOtherEmergency('FREEZE')}
                className="py-1.5 rounded-lg text-[10px] font-bold uppercase
                           bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300
                           border border-[#00D9FF]/50 transition-all"
              >
                Freeze
              </button>
            </div>
          </div>
        </Card>

        {/* --- Correlation Matrix (API only; cell click → drill-down) --- */}
        <Card title="Correlation Matrix" className="col-span-1 md:col-span-3"
              action={<Grid3X3 className="w-4 h-4 text-[#00D9FF]" />}>
          <CorrelationHeatmap
            data={correlationData}
            loading={correlationLoading}
            onCellClick={(sym1) => navigate(`/symbol/${encodeURIComponent(sym1)}`)}
          />
          {correlationDrill && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={() => setCorrelationDrill(null)}>
              <div className="bg-[#111827] border border-cyan-500/40 rounded-xl p-4 max-w-xs w-full mx-2" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-cyan-400 font-mono text-sm font-bold">Correlation drill-down</span>
                  <button onClick={() => setCorrelationDrill(null)} className="text-gray-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <div className="text-[10px] font-mono text-gray-300 space-y-1">
                  <div>{correlationDrill.sym1} vs {correlationDrill.sym2}</div>
                  <div style={{ color: C.cyan }}>Correlation: {(Number(correlationDrill?.value) ?? 0).toFixed(3)}</div>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* --- Volatility Regime Monitor (API only) --- */}
        <Card title="Volatility Regime Monitor" className="col-span-1 md:col-span-2"
              action={<Gauge className="w-4 h-4 text-[#00D9FF]" />}>
          <div className="space-y-2.5">
            {volRegimeItems.length === 0 && !riskData && <Skeleton className="w-full h-16" />}
            {volRegimeItems.map((item, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400">{item.label}</span>
                  <span className="font-mono font-bold" style={{ color: item.color }}>
                    {typeof item.value === 'number' ? item.value.toFixed(1) : item.value}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#0B0E14] rounded overflow-hidden">
                  <div className="h-full rounded transition-all duration-500"
                       style={{
                         width: `${Math.min((typeof item.value === 'number' ? item.value / item.max : 0) * 100, 100)}%`,
                         backgroundColor: item.color + 'B0',
                       }} />
                </div>
              </div>
            ))}
            <div className="mt-2 p-2 bg-[#0B0E14] border border-[rgba(42,52,68,0.5)]/50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-500">Current Regime</span>
                <span className="text-[10px] font-mono font-bold" style={{ color: C.green }}>
                  {riskData?.volatility_regime ?? regimeData?.state ?? '—'}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-gray-500">Regime Confidence</span>
                <span className="text-[10px] font-mono font-bold" style={{ color: C.cyan }}>
                  {riskData?.regime_confidence != null ? String(riskData.regime_confidence) : (regimeData?.confidence != null ? `${(regimeData.confidence * 100).toFixed(0)}%` : '—')}
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* --- AI Agent Risk Monitors (API only) --- */}
        <Card title="AI Agent Risk Monitors" className="col-span-1 md:col-span-3"
              action={<Brain className="w-4 h-4 text-[#00D9FF]" />}>
          <div className="space-y-2">
            {agentMonitors.length === 0 && !monte && !kelly && <Skeleton className="w-full h-20" />}
            {agentMonitors.length === 0 && (monte || kelly) && (
              <div className="flex flex-col items-center justify-center py-4 text-gray-500">
                <Brain className="w-5 h-5 mb-1 opacity-40" />
                <div className="text-[10px] font-mono">No agents reporting risk data</div>
              </div>
            )}
            {agentMonitors.map((item, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400">{item.label}</span>
                  <span className="font-mono font-bold" style={{ color: item.color }}>
                    {typeof item.value === 'number' ? Math.round(item.value) : '--'}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#0B0E14] rounded overflow-hidden">
                  <div className="h-full rounded transition-all duration-500"
                       style={{
                         width: `${Math.min(Math.max(item.value, 0), 100)}%`,
                         backgroundColor: item.color + 'B0',
                       }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* --- Position Sizing (API only) --- */}
        <Card title="Position Sizing" className="col-span-1 md:col-span-2"
              action={<DollarSign className="w-4 h-4 text-[#00D9FF]" />}>
          <PositionSizer kelly={kelly} portfolioValue={portfolioValue} loading={kellyLoading} />
        </Card>
      </div>
      </SectionErrorBoundary>

      {/* ════════════════════════════════════════════════════════════════════════
          ROW 3: Risk Interdependencies
          ════════════════════════════════════════════════════════════════════════ */}
      <Card title="Risk Interdependencies"
            subtitle="Cross-factor dependency analysis (API-driven)"
            action={<Target className="w-4 h-4 text-[#00D9FF]" />}>
        <div className="overflow-auto custom-scrollbar py-4 text-center text-[10px] font-mono text-gray-500">
          No interdependency data — use risk API for cross-factor analysis.
        </div>
      </Card>

      {/* ════════════════════════════════════════════════════════════════════════
          ROW 4: Risk Event Timeline
          ════════════════════════════════════════════════════════════════════════ */}
      <Card title="Risk Event Timeline"
            subtitle="Horizontal risk exposure over time"
            action={<Clock className="w-4 h-4 text-[#00D9FF]" />}>
        <div className="py-4 text-center text-[10px] font-mono text-gray-500">
          No timeline data — wire to risk history API for event exposure.
        </div>
      </Card>

      {/* ════════════════════════════════════════════════════════════════════════
          BOTTOM: 90-Day Risk History (data table)
          ════════════════════════════════════════════════════════════════════════ */}
      <SectionErrorBoundary name="Risk History">
      <Card title="90-Day Risk History"
            action={
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: C.green }} />
                  <span className="text-[9px] text-gray-500">Low</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: C.amber }} />
                  <span className="text-[9px] text-gray-500">Medium</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: C.red }} />
                  <span className="text-[9px] text-gray-500">High</span>
                </div>
              </div>
            }>
        <div className="overflow-auto custom-scrollbar">
          <table className="w-full text-[10px] font-mono border-collapse">
            <thead>
              <tr className="text-[9px] text-gray-500 uppercase tracking-wider border-b border-[rgba(42,52,68,0.5)]">
                <th className="py-1.5 px-2 text-left">Date</th>
                <th className="py-1.5 px-2 text-right">Score</th>
                <th className="py-1.5 px-2 text-right">VaR</th>
                <th className="py-1.5 px-2 text-right">DD%</th>
                <th className="py-1.5 px-2 text-right">Vol</th>
                <th className="py-1.5 px-2 text-right">Beta</th>
                <th className="py-1.5 px-2 text-right">Sharpe</th>
                <th className="py-1.5 px-2 text-center">Regime</th>
                <th className="py-1.5 px-2 text-center">Status</th>
                <th className="py-1.5 px-2 text-left" style={{ width: '15%' }}>Risk Bar</th>
              </tr>
            </thead>
            <tbody>
              {historyTableRows.map((row, ri) => {
                const score = row.score ?? 0;
                const scoreColor = score <= 35 ? C.green : score <= 65 ? C.amber : C.red;
                const st = row.status ?? (score <= 35 ? 'SAFE' : score <= 65 ? 'CAUTION' : 'DANGER');
                const stColor = st === 'SAFE' ? C.green : st === 'CAUTION' ? C.amber : C.red;
                return (
                  <tr
                    key={ri}
                    role="button"
                    tabIndex={0}
                    onClick={() => setHistoryDayDetail(row)}
                    className="border-b border-[rgba(42,52,68,0.25)] hover:bg-[rgba(42,52,68,0.12)] transition-colors cursor-pointer"
                  >
                    <td className="py-1 px-2 text-gray-400">{row.date}</td>
                    <td className="py-1 px-2 text-right font-bold" style={{ color: scoreColor }}>{score}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.var95 ?? row.var ?? '--'}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.drawdown ?? row.dd ?? (row.maxDailyLoss != null ? (row.maxDailyLoss * 100).toFixed(1) : '--')}%</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.vol ?? '--'}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.beta ?? '--'}</td>
                    <td className="py-1 px-2 text-right text-slate-300">{row.sharpe ?? '--'}</td>
                    <td className="py-1 px-2 text-center">
                      <span className="text-[8px]" style={{ color: C.cyan }}>{row.regime ?? '--'}</span>
                    </td>
                    <td className="py-1 px-2 text-center">
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-bold"
                            style={{ backgroundColor: stColor + '18', color: stColor }}>
                        <span className="w-1 h-1 rounded-full" style={{ backgroundColor: stColor }} />
                        {st}
                      </span>
                    </td>
                    <td className="py-1 px-2">
                      <div className="w-full h-2 bg-[#0B0E14] rounded overflow-hidden">
                        <div className="h-full rounded transition-all"
                             style={{ width: `${Math.min(score, 100)}%`, backgroundColor: scoreColor + 'B0' }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {historyDayDetail && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={() => setHistoryDayDetail(null)}>
            <div className="bg-[#111827] border border-cyan-500/40 rounded-xl p-4 max-w-sm w-full mx-2" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-cyan-400 font-mono text-sm font-bold">Day risk breakdown</span>
                <button onClick={() => setHistoryDayDetail(null)} className="text-gray-400 hover:text-white"><X className="w-4 h-4" /></button>
              </div>
              <div className="text-[10px] font-mono text-gray-300 space-y-1">
                <div>Date: {historyDayDetail.date}</div>
                <div>Score: {historyDayDetail.score ?? '—'}</div>
                <div>VaR 95%: {historyDayDetail.var95 ?? historyDayDetail.var ?? '—'}</div>
                <div>Drawdown: {historyDayDetail.drawdown ?? historyDayDetail.dd ?? (historyDayDetail.maxDailyLoss != null ? (historyDayDetail.maxDailyLoss * 100).toFixed(1) + '%' : '—')}</div>
                <div>Vol: {historyDayDetail.vol ?? '—'}</div>
                <div>Regime: {historyDayDetail.regime ?? '—'}</div>
                <div>Status: {historyDayDetail.status ?? '—'}</div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* VaR & Stress Testing — custom scenarios, run via API */}
      <Card title="VaR & Stress Testing" subtitle="Run Monte Carlo stress test" action={<Gauge className="w-4 h-4 text-[#00D9FF]" />}>
        <div className="space-y-3">
          <button
            onClick={runStressTest}
            disabled={stressLoading}
            className="px-4 py-2 rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 border border-cyan-500/40 text-xs font-mono font-bold uppercase disabled:opacity-50"
          >
            {stressLoading ? 'Running…' : 'Run stress test'}
          </button>
          {stressResult && (
            <div className="text-[10px] font-mono text-gray-300 space-y-1 p-2 bg-[#0B0E14] rounded-lg">
              {stressResult.error ? (
                <div className="text-red-400">{stressResult.error}</div>
              ) : (
                <>
                  <div>VaR 95%: {stressResult.var_95 != null ? stressResult.var_95 : '—'}</div>
                  <div>CVaR 95%: {stressResult.cvar_95 != null ? stressResult.cvar_95 : '—'}</div>
                  <div>Worst case: {stressResult.worst_case != null ? stressResult.worst_case : '—'}</div>
                </>
              )}
            </div>
          )}
        </div>
      </Card>
      </SectionErrorBoundary>

      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          FOOTER (mockup: aligns with system footer style)
          ════════════════════════════════════════════════════════════════════════ */}
      <footer className="mt-3 px-4 py-2 border border-[rgba(42,52,68,0.5)] rounded-lg flex items-center justify-between
                         text-[10px] text-[#94a3b8] font-mono bg-[#111827]">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <Radio className="w-3 h-3 text-[#00D9FF]" />
          Embodier Trader -- Risk Intelligence v2.0
        </span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: C.green }} />
            Shields: ACTIVE
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: C.cyan }} />
            Risk Engine: ONLINE
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: C.green }} />
            Monte Carlo: READY
          </span>
        </div>
        <span className="text-[#94a3b8]">
          Embodier Trader - Risk Intelligence v2.0 | Refresh: {lastRefresh.toLocaleTimeString()}
        </span>
      </footer>
    </div>
  );
}
