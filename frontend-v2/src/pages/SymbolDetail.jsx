// SymbolDetail — full analysis view for a single symbol. All data via useApi(); no mock data.
import React, { useRef, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { createChart, CrosshairMode, LineStyle } from "lightweight-charts";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import {
  ArrowLeft,
  TrendingUp,
  Shield,
  Target,
  BarChart2,
  MessageSquare,
  AlertTriangle,
} from "lucide-react";

const REGIME_BADGE = {
  GREEN: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  YELLOW: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  RED: "bg-red-500/20 text-red-400 border-red-500/30",
  CRISIS: "bg-gray-800 text-gray-300 border-gray-600",
};

function PriceChart({ bars, loading }) {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current || !bars?.length) return;
    if (chartInstance.current) {
      chartInstance.current.remove();
      chartInstance.current = null;
    }
    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#94a3b8",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#334155", style: LineStyle.Solid },
        horzLines: { color: "#334155", style: LineStyle.Solid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: {
        borderColor: "#475569",
        timeVisible: true,
        secondsVisible: false,
        rightBarSpacing: 8,
        barSpacing: 3,
        minBarSpacing: 2,
        visible: true,
      },
      rightPriceScale: {
        borderColor: "#475569",
        scaleMargins: { top: 0.1, bottom: 0.15 },
        precision: 2,
      },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });
    // Lightweight Charts requires strictly ascending unique times — dedupe by time (keep last per time)
    const sorted = [...bars].sort((a, b) => a.time - b.time);
    const byTime = new Map();
    for (const b of sorted) byTime.set(b.time, b);
    const strictAsc = Array.from(byTime.values()).sort((a, b) => a.time - b.time);
    candleSeries.setData(strictAsc);
    chart.timeScale().fitContent();
    chartInstance.current = chart;
    return () => {
      if (chartInstance.current) {
        chartInstance.current.remove();
        chartInstance.current = null;
      }
    };
  }, [bars]);

  if (loading) {
    return (
      <div className="min-h-[520px] rounded-lg border border-white/10 bg-white/5 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!bars?.length) {
    return (
      <div className="min-h-[520px] rounded-lg border border-white/10 bg-white/5 flex items-center justify-center text-gray-500 text-sm">
        No chart data
      </div>
    );
  }
  return <div ref={chartRef} className="min-h-[520px] w-full rounded-lg" style={{ height: "520px" }} />;
}

export default function SymbolDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const symbol = (ticker || "").toUpperCase().trim();

  // Chart: daily bars, high limit for symbol detail (up to ~2 years)
  const { data: quoteData, loading: quoteLoading } = useApi("quotes", {
    endpoint: symbol ? `/quotes/${symbol}?timeframe=1D&limit=500` : null,
    enabled: !!symbol,
  });
  const { data: signalsData } = useApi("signals", { enabled: !!symbol });
  const { data: technicalsData } = useApi("signals", {
    endpoint: symbol ? `/signals/${symbol}/technicals` : null,
    enabled: !!symbol,
  });
  const { data: councilHistoryData } = useApi("councilHistory", {
    endpoint: symbol ? `/council/history?symbol=${encodeURIComponent(symbol)}` : null,
    enabled: !!symbol,
  });
  const { data: councilLatestData } = useApi("councilLatest", { enabled: !!symbol });
  const { data: riskProposalData } = useApi("riskScore", {
    endpoint: symbol ? `/risk/proposal/${symbol}` : null,
    enabled: !!symbol,
  });
  const { data: featuresData } = useApi("featuresLatest", {
    endpoint: symbol ? `/features/latest?symbol=${encodeURIComponent(symbol)}` : null,
    enabled: !!symbol,
  });
  const { data: sentimentData } = useApi("sentiment", { enabled: !!symbol });
  const { data: briefingData } = useApi("briefingTradingview", { enabled: !!symbol });
  const { data: riskScoreData } = useApi("riskScore", { enabled: !!symbol });

  const bars = useMemo(() => {
    const raw = quoteData?.bars ?? quoteData?.data ?? [];
    if (!Array.isArray(raw) || raw.length === 0) return [];
    return raw
      .map((b) => {
        const t = b.timestamp ?? b.t ?? b.time;
        const ts = t != null ? Math.floor(new Date(t).getTime() / 1000) : null;
        const open = Number(b.open ?? b.o);
        const high = Number(b.high ?? b.h);
        const low = Number(b.low ?? b.l);
        const close = Number(b.close ?? b.c);
        if (!Number.isFinite(ts) || !Number.isFinite(close)) return null;
        return { time: ts, open, high, low, close };
      })
      .filter(Boolean)
      .sort((a, b) => a.time - b.time);
  }, [quoteData]);

  const lastBar = bars.length ? bars[bars.length - 1] : null;
  const prevBar = bars.length > 1 ? bars[bars.length - 2] : null;
  const dailyChangePct =
    lastBar && prevBar && prevBar.close
      ? ((lastBar.close - prevBar.close) / prevBar.close) * 100
      : null;

  const signalForSymbol = useMemo(() => {
    const list = signalsData?.signals ?? (Array.isArray(signalsData) ? signalsData : []);
    const arr = Array.isArray(list) ? list : [];
    return arr.find((s) => (s.symbol || s.ticker || "").toUpperCase() === symbol) ?? null;
  }, [signalsData, symbol]);

  const councilDecisions = councilHistoryData?.decisions ?? [];
  const latestCouncil = councilDecisions[0] ?? null;
  const councilVerdict =
    latestCouncil ??
    (councilLatestData?.symbol?.toUpperCase() === symbol ? councilLatestData : null);

  const sentimentItem = useMemo(() => {
    const items = sentimentData?.items ?? (Array.isArray(sentimentData) ? sentimentData : []);
    return (Array.isArray(items) ? items : []).find(
      (i) => (i.ticker || i.symbol || "").toUpperCase() === symbol
    );
  }, [sentimentData, symbol]);

  const tradeIdea = useMemo(() => {
    const ideas = briefingData?.trade_ideas ?? briefingData?.ideas ?? [];
    return (Array.isArray(ideas) ? ideas : []).find(
      (i) => (i.symbol || i.ticker || "").toUpperCase() === symbol
    );
  }, [briefingData, symbol]);

  // Normalize regime to string (API may return object e.g. { state: "green" } or string "GREEN")
  const regimeRaw =
    councilVerdict?.regime ??
    signalForSymbol?.scores?.regime ??
    briefingData?.regime?.state ??
    "GREEN";
  const regime =
    typeof regimeRaw === "string"
      ? regimeRaw
      : (regimeRaw && typeof regimeRaw === "object" && regimeRaw.state != null
          ? regimeRaw.state
          : "GREEN");
  const regimeStr = String(regime ?? "GREEN").toUpperCase();
  const regimeClass = REGIME_BADGE[regimeStr] ?? REGIME_BADGE.GREEN;

  if (!symbol) {
    return (
      <div className="p-6">
        <p className="text-gray-400">No symbol specified.</p>
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="mt-4 px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 text-sm"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header: back, symbol, price, change %, regime */}
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-gray-400 hover:text-cyan-400 text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h1 className="text-2xl font-bold font-mono text-white">{symbol}</h1>
        {lastBar && (
          <span className="text-lg font-mono text-white">
            ${Number(lastBar.close).toFixed(2)}
          </span>
        )}
        {dailyChangePct != null && (
          <span
            className={`text-sm font-mono font-medium ${
              dailyChangePct >= 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {dailyChangePct >= 0 ? "+" : ""}
            {dailyChangePct.toFixed(2)}%
          </span>
        )}
        <span className={`px-2 py-1 rounded border text-xs font-medium ${regimeClass}`}>
          {regimeStr || "—"}
        </span>
      </div>

      {/* Price chart */}
      <section>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5" /> Price chart
        </h2>
        <PriceChart bars={bars} loading={quoteLoading} />
      </section>

      <div className="grid gap-6 sm:grid-cols-2">
        {/* Council verdict */}
        <section className="rounded-lg border border-white/10 bg-white/5 p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5" /> Council verdict
          </h2>
          {councilVerdict ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Direction:</span>
                <span
                  className={
                    (councilVerdict.direction ?? councilVerdict.verdict ?? "").toUpperCase() === "BUY"
                      ? "text-emerald-400 font-medium"
                      : (councilVerdict.direction ?? councilVerdict.verdict ?? "").toUpperCase() ===
                          "SELL"
                        ? "text-red-400 font-medium"
                        : "text-amber-400 font-medium"
                  }
                >
                  {(councilVerdict.direction ?? councilVerdict.verdict ?? "HOLD").toUpperCase()}
                </span>
              </div>
              {councilVerdict.confidence != null && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">Confidence:</span>
                  <span className="text-cyan-400 font-mono">
                    {(Number(councilVerdict.confidence) * 100).toFixed(0)}%
                  </span>
                </div>
              )}
              {councilDecisions.length > 0 && (
                <p className="text-xs text-gray-500 mt-2">
                  {councilDecisions.length} decision(s) in history
                </p>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No council verdict for this symbol yet.</p>
          )}
        </section>

        {/* Signal scores */}
        <section className="rounded-lg border border-white/10 bg-white/5 p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Target className="w-3.5 h-3.5" /> Signal scores
          </h2>
          {signalForSymbol ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Composite:</span>
                <span className="font-mono text-cyan-400">{signalForSymbol.score ?? "—"}</span>
              </div>
              {signalForSymbol.scores && (
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
                  {Object.entries(signalForSymbol.scores).map(([k, v]) => (
                    <span key={k}>
                      {k}: <span className="text-gray-300 font-mono">{v ?? "—"}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No signal data for this symbol.</p>
          )}
        </section>

        {/* Technicals (RSI, MACD, etc.) */}
        <section className="rounded-lg border border-white/10 bg-white/5 p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5" /> Technicals
          </h2>
          {technicalsData?.technicals ? (
            <div className="grid grid-cols-2 gap-2 text-sm font-mono">
              <div><span className="text-gray-500">RSI:</span> <span className="text-cyan-400">{technicalsData.technicals.rsi ?? "—"}</span></div>
              <div><span className="text-gray-500">MACD:</span> <span className="text-cyan-400">{technicalsData.technicals.macd ?? "—"}</span></div>
              <div><span className="text-gray-500">BB:</span> <span className="text-white">{technicalsData.technicals.bb ?? "—"}</span></div>
              <div><span className="text-gray-500">VWAP:</span> <span className="text-cyan-400">{technicalsData.technicals.vwap ?? "—"}</span></div>
              <div><span className="text-gray-500">EMA 20:</span> <span className="text-white">{technicalsData.technicals.ema20 ?? "—"}</span></div>
              <div><span className="text-gray-500">SMA 50:</span> <span className="text-emerald-400">{technicalsData.technicals.sma50 ?? "—"}</span></div>
              <div><span className="text-gray-500">ADX:</span> <span className="text-white">{technicalsData.technicals.adx ?? "—"}</span></div>
              <div><span className="text-gray-500">Stoch:</span> <span className="text-emerald-400">{technicalsData.technicals.stoch ?? "—"}</span></div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No technical data for this symbol.</p>
          )}
        </section>

        {/* Trade levels (from briefing) */}
        <section className="rounded-lg border border-white/10 bg-white/5 p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Target className="w-3.5 h-3.5" /> Trade levels
          </h2>
          {tradeIdea ? (
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-gray-400">Entry:</span>
              <span className="font-mono text-white">
                {tradeIdea.entry_zone?.[0] ?? tradeIdea.entry ?? tradeIdea.price ?? "—"}
              </span>
              <span className="text-gray-400">Stop:</span>
              <span className="font-mono text-red-400">
                {tradeIdea.stop_loss ?? tradeIdea.stop ?? "—"}
              </span>
              <span className="text-gray-400">Target 1:</span>
              <span className="font-mono text-emerald-400">
                {tradeIdea.target_1 ?? tradeIdea.target1 ?? "—"}
              </span>
              <span className="text-gray-400">Target 2:</span>
              <span className="font-mono text-emerald-400">
                {tradeIdea.target_2 ?? tradeIdea.target2 ?? "—"}
              </span>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Not in today&apos;s trade ideas.</p>
          )}
        </section>

        {/* Sentiment */}
        <section className="rounded-lg border border-white/10 bg-white/5 p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <MessageSquare className="w-3.5 h-3.5" /> Sentiment
          </h2>
          {sentimentItem ? (
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Score:</span>
                <span className="font-mono text-cyan-400">
                  {sentimentItem.overallScore ?? sentimentItem.score ?? "—"}
                </span>
              </div>
              {sentimentItem.headlines?.length > 0 && (
                <ul className="mt-2 text-xs text-gray-400 list-disc list-inside">
                  {sentimentItem.headlines.slice(0, 3).map((h, i) => (
                    <li key={i}>{typeof h === "string" ? h : h?.title ?? h?.text ?? "—"}</li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No sentiment data for this symbol.</p>
          )}
        </section>
      </div>

      {/* Risk */}
      <section className="rounded-lg border border-white/10 bg-white/5 p-4">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Shield className="w-3.5 h-3.5" /> Risk
        </h2>
        <div className="flex flex-wrap gap-6 text-sm">
          {riskScoreData && (
            <div>
              <span className="text-gray-400">Portfolio risk score: </span>
              <span className="font-mono text-amber-400">{riskScoreData.score ?? "—"}</span>
            </div>
          )}
          {riskProposalData && (
            <>
              <div>
                <span className="text-gray-400">Max notional: </span>
                <span className="font-mono text-cyan-400">
                  ${Number(riskProposalData.maxNotional ?? 0).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Position size limit: </span>
                <span className="font-mono text-cyan-400">
                  {riskProposalData.positionSizeLimit ?? "—"}
                </span>
              </div>
              {riskProposalData.equity != null && (
                <div>
                  <span className="text-gray-400">Equity: </span>
                  <span className="font-mono text-white">${Number(riskProposalData.equity).toLocaleString()}</span>
                </div>
              )}
              {riskProposalData.buyingPower != null && (
                <div>
                  <span className="text-gray-400">Buying power: </span>
                  <span className="font-mono text-emerald-400">${Number(riskProposalData.buyingPower).toLocaleString()}</span>
                </div>
              )}
              {riskProposalData.proposal && (
                <>
                  {riskProposalData.proposal.proposedSize != null && (
                    <div>
                      <span className="text-gray-400">Proposed size: </span>
                      <span className="font-mono text-cyan-400">{riskProposalData.proposal.proposedSize} shares</span>
                    </div>
                  )}
                  {riskProposalData.proposal.kellyPercent != null && (
                    <div>
                      <span className="text-gray-400">Kelly %: </span>
                      <span className="font-mono text-cyan-400">{riskProposalData.proposal.kellyPercent}%</span>
                    </div>
                  )}
                  {riskProposalData.proposal.limitPrice != null && riskProposalData.proposal.limitPrice > 0 && (
                    <div>
                      <span className="text-gray-400">Limit: </span>
                      <span className="font-mono text-white">${Number(riskProposalData.proposal.limitPrice).toFixed(2)}</span>
                    </div>
                  )}
                  {riskProposalData.proposal.stopLoss != null && riskProposalData.proposal.stopLoss > 0 && (
                    <div>
                      <span className="text-gray-400">Stop: </span>
                      <span className="font-mono text-red-400">${Number(riskProposalData.proposal.stopLoss).toFixed(2)}</span>
                    </div>
                  )}
                  {riskProposalData.proposal.takeProfit != null && riskProposalData.proposal.takeProfit > 0 && (
                    <div>
                      <span className="text-gray-400">Target: </span>
                      <span className="font-mono text-emerald-400">${Number(riskProposalData.proposal.takeProfit).toFixed(2)}</span>
                    </div>
                  )}
                  {riskProposalData.proposal.rMultiple != null && (
                    <div>
                      <span className="text-gray-400">R-multiple: </span>
                      <span className="font-mono text-cyan-400">{Number(riskProposalData.proposal.rMultiple).toFixed(1)}R</span>
                    </div>
                  )}
                </>
              )}
            </>
          )}
          {!riskProposalData && !riskScoreData && (
            <p className="text-gray-500">No risk data available.</p>
          )}
        </div>
      </section>

      {/* Features (latest) */}
      {featuresData?.status === "ok" && (
        <section className="rounded-lg border border-white/10 bg-white/5 p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5" /> Feature vector
          </h2>
          <p className="text-xs text-gray-500">
            Pipeline: {featuresData.pipeline_version ?? "—"} · Timeframe: {featuresData.timeframe ?? "—"}
          </p>
        </section>
      )}
    </div>
  );
}
