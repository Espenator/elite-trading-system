// PERFORMANCE ANALYTICS - Embodier Trader
// GET /api/v1/performance - market stats, summary, monthly returns, factors
// GET /api/v1/performance/equity-curve - equity curve timeseries
// GET /api/v1/performance/sharpe - rolling sharpe ratio
// GET /api/v1/performance/factors - factor decomposition
// GET /api/v1/performance/cumulative - cumulative returns vs benchmarks
// GET /api/v1/performance/distribution - trade P&L distribution
// GET /api/v1/performance/ml-insights - ML model insights & accuracy
// GET /api/v1/agents/consensus - agent voting consensus
import { useState, useEffect, useRef, useCallback } from "react";
import { Download, TrendingUp, TrendingDown, Activity, Target, Zap, Shield, Brain, BarChart3, PieChart as PieIcon } from "lucide-react";
import { AreaChart, Area, LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const CONSENSUS_COLORS = ["#10b981", "#f43f5e", "#64748b"];
const KPI_ICONS = [Activity, Target, Zap, TrendingUp, Shield, BarChart3, Brain, PieIcon];

// === Lightweight Charts Equity Curve ===
function EquityCurveLC({ data, height = 220 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    let chart;
    const init = async () => {
      try {
        const mod = await import("lightweight-charts");
        const createChart = mod.createChart;
        if (!containerRef.current) return;
        chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height,
          layout: { background: { color: "transparent" }, textColor: "#94a3b8" },
          grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
          crosshair: { mode: 0 },
          timeScale: { borderColor: "#334155", timeVisible: true },
          rightPriceScale: { borderColor: "#334155" },
        });
        const series = chart.addAreaSeries({ lineColor: "#10b981", topColor: "rgba(16,185,129,0.4)", bottomColor: "rgba(16,185,129,0.0)", lineWidth: 2 });
        if (Array.isArray(data) && data.length > 0) {
          const mapped = data.map(d => ({ time: d.time || d.date || d.t, value: d.value || d.close || d.v })).filter(d => d.time && d.value != null);
          if (mapped.length) series.setData(mapped);
        }
        chartRef.current = chart;
        const ro = new ResizeObserver(() => { if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth }); });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
      } catch (e) { console.warn("lightweight-charts not available:", e); }
    };
    init();
    return () => { if (chart) chart.remove(); };
  }, [data, height]);
  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

// === Drawdown Lightweight Chart ===
function DrawdownLC({ data, height = 60 }) {
  const containerRef = useRef(null);
  useEffect(() => {
    let chart;
    const init = async () => {
      try {
        const mod = await import("lightweight-charts");
        const createChart = mod.createChart;
        if (!containerRef.current) return;
        chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth, height,
          layout: { background: { color: "transparent" }, textColor: "#94a3b8" },
          grid: { vertLines: { visible: false }, horzLines: { color: "#1e293b" } },
          timeScale: { visible: false }, rightPriceScale: { borderColor: "#334155" },
        });
        const series = chart.addAreaSeries({ lineColor: "#f43f5e", topColor: "rgba(244,63,94,0.0)", bottomColor: "rgba(244,63,94,0.3)", lineWidth: 1 });
        if (Array.isArray(data) && data.length > 0) {
          const mapped = data.map(d => ({ time: d.time || d.date || d.t, value: d.value || d.drawdown || d.v })).filter(d => d.time && d.value != null);
          if (mapped.length) series.setData(mapped);
        }
        const ro = new ResizeObserver(() => { if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth }); });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
      } catch (e) { console.warn("DrawdownLC not available:", e); }
    };
    init();
    return () => { if (chart) chart.remove(); };
  }, [data, height]);
  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

// === ReactFlow Swarm Brain Map ===
function SwarmBrainMap({ data }) {
  const mapRef = useRef(null);
  useEffect(() => {
    const init = async () => {
      try {
        const rf = await import("reactflow");
        await import("reactflow/dist/style.css");
        if (!mapRef.current) return;
        const nodes = (data?.nodes || [
          { id: "1", data: { label: "AI Core" }, position: { x: 250, y: 0 }, style: { background: "#10b981", color: "#fff", border: "1px solid #059669", borderRadius: 8, padding: 10, fontSize: 11 } },
          { id: "2", data: { label: "Momentum Agent" }, position: { x: 100, y: 100 }, style: { background: "#0f172a", color: "#10b981", border: "1px solid #10b981", borderRadius: 8, padding: 8, fontSize: 10 } },
          { id: "3", data: { label: "Mean Rev Agent" }, position: { x: 250, y: 100 }, style: { background: "#0f172a", color: "#3b82f6", border: "1px solid #3b82f6", borderRadius: 8, padding: 8, fontSize: 10 } },
          { id: "4", data: { label: "Sentiment Agent" }, position: { x: 400, y: 100 }, style: { background: "#0f172a", color: "#8b5cf6", border: "1px solid #8b5cf6", borderRadius: 8, padding: 8, fontSize: 10 } },
          { id: "5", data: { label: "Risk Manager" }, position: { x: 175, y: 200 }, style: { background: "#0f172a", color: "#f59e0b", border: "1px solid #f59e0b", borderRadius: 8, padding: 8, fontSize: 10 } },
          { id: "6", data: { label: "Executor" }, position: { x: 325, y: 200 }, style: { background: "#0f172a", color: "#ef4444", border: "1px solid #ef4444", borderRadius: 8, padding: 8, fontSize: 10 } },
        ]);
        const edges = (data?.edges || [
          { id: "e1-2", source: "1", target: "2", animated: true, style: { stroke: "#10b981" } },
          { id: "e1-3", source: "1", target: "3", animated: true, style: { stroke: "#3b82f6" } },
          { id: "e1-4", source: "1", target: "4", animated: true, style: { stroke: "#8b5cf6" } },
          { id: "e2-5", source: "2", target: "5", animated: true, style: { stroke: "#f59e0b" } },
          { id: "e3-5", source: "3", target: "5", animated: true, style: { stroke: "#f59e0b" } },
          { id: "e4-6", source: "4", target: "6", animated: true, style: { stroke: "#ef4444" } },
          { id: "e5-6", source: "5", target: "6", animated: true, style: { stroke: "#ef4444" } },
        ]);
        const root = document.createElement("div");
        root.style.cssText = "width:100%;height:100%;";
        mapRef.current.innerHTML = "";
        mapRef.current.appendChild(root);
        const { createRoot } = await import("react-dom/client");
        const React = await import("react");
        const rr = createRoot(root);
        rr.render(React.createElement(rf.ReactFlowProvider, null, React.createElement(rf.default || rf.ReactFlow, { nodes, edges, fitView: true, nodesDraggable: true, nodesConnectable: false, proOptions: { hideAttribution: true }, style: { background: "transparent" } })));
      } catch (e) { console.warn("ReactFlow not available:", e); if (mapRef.current) mapRef.current.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;font-size:11px">Install reactflow for Swarm Brain Map</div>'; }
    };
    init();
  }, [data]);
  return <div ref={mapRef} style={{ width: "100%", height: 240 }} />;
}

// === MarketStat Helper ===
function MarketStat({ label, value, change, sub, up }) {
  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl p-4">
      <div className="text-xs text-secondary mb-1">{label}</div>
      <div className="text-xl font-bold text-white">{value}</div>
      {change && (
        <div className={`flex items-center gap-1 text-xs mt-1 ${up ? "text-success" : "text-danger"}`}>
          {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {change}
        </div>
      )}
      {sub && (<div className={`text-xs mt-1 ${up ? "text-emerald-400" : "text-gray-400"}`}>{sub}</div>)}
    </div>
  );
}

// === Default Fallback Data ===
const defaultKpis = [
  { label: "Total Return", value: "+32.4%", sub: "+2.1% today" },
  { label: "Sharpe Ratio", value: "2.45", sub: "Excellent" },
  { label: "Max Drawdown", value: "-8.2%", sub: "Controlled" },
  { label: "Win Rate", value: "68.5%", sub: "642/937" },
  { label: "Profit Factor", value: "2.85", sub: "Strong" },
  { label: "Avg Trade", value: "+$245", sub: "Per trade" },
  { label: "Total Trades", value: "937", sub: "This period" },
  { label: "Alpha", value: "+4.2%", sub: "vs S&P 500" },
];

const defaultShap = [
  { name: "RSI Signal", value: 35 }, { name: "MACD Cross", value: 28 },
  { name: "Volume Spike", value: 22 }, { name: "Price Action", value: 18 },
  { name: "Sentiment", value: 15 }, { name: "Volatility", value: 12 },
  { name: "Momentum", value: 10 }, { name: "Correlation", value: 8 },
];

const defaultConsensus = [
  { name: "Bull", value: 65 }, { name: "Bear", value: 20 }, { name: "Neutral", value: 15 },
];

// === Main Component ===
export default function PerformanceAnalytics() {
  const [timeframe, setTimeframe] = useState("1W");
  const timeframes = ["1H", "4H", "1D", "1W", "1M", "3M", "6M", "YTD", "ALL"];

  // API calls
  const { data, loading, error, refetch } = useApi("performance", { pollIntervalMs: 60000 });
  const { data: sharpeData } = useApi("performance/sharpe", { pollIntervalMs: 120000 });
  const { data: factorData } = useApi("performance/factors", { pollIntervalMs: 120000 });
  const { data: cumulData } = useApi("performance/cumulative", { pollIntervalMs: 120000 });
  const { data: distData } = useApi("performance/distribution", { pollIntervalMs: 120000 });
  const { data: mlData } = useApi("performance/ml-insights", { pollIntervalMs: 120000 });
  const { data: consensusData } = useApi("agents/consensus", { pollIntervalMs: 30000 });
  const { data: equityData } = useApi("performance/equity-curve", { pollIntervalMs: 60000 });

  // Extracted data with fallbacks
  const marketStats = Array.isArray(data?.marketStats) ? data.marketStats : [];
  const summary = Array.isArray(data?.summary) ? data.summary : [];
  const monthlyReturns = data?.monthlyReturns ?? {};
  const factors = Array.isArray(data?.factors) ? data.factors : [];
  const portfolioValue = data?.portfolioValue ?? null;
  const dailyPnL = data?.dailyPnL ?? null;
  const dailyPnLPct = data?.dailyPnLPct ?? null;
  const kpis = data?.kpis || defaultKpis;
  const shap = data?.shap || defaultShap;
  const consensus = consensusData?.votes || defaultConsensus;

  // Rolling Sharpe
  const rollingSharpe = sharpeData?.series || Array.from({ length: 24 }, (_, i) => ({ month: `${2023 + Math.floor(i/12)}-${String(i%12+1).padStart(2,"0")}`, value: 1.5 + Math.random() * 1.5 - 0.1 + Math.sin(i/4) * 0.5 }));

  // Factor Decomposition
  const factorDecomp = factorData?.decomposition || [
    { name: "Momentum", value: 25 }, { name: "Value", value: 22 },
    { name: "Growth", value: 18 }, { name: "Quality", value: 12 },
    { name: "Size", value: 8 }, { name: "Volatility", value: -15 },
  ];

  // Cumulative Returns
  const cumulReturns = cumulData?.series || Array.from({ length: 24 }, (_, i) => ({ month: `${2023 + Math.floor(i/12)}-${String(i%12+1).padStart(2,"0")}`, strategy: 100 + i * 7 + Math.random() * 10, spy: 100 + i * 4 + Math.random() * 5, qqq: 100 + i * 5 + Math.random() * 7 }));

  // Trade P&L Distribution
  const tradeDist = distData?.distribution || Array.from({ length: 20 }, (_, i) => ({ range: `${(i-10)*200}`, count: Math.floor(Math.random() * 80 + 10) }));

  // Market Overview
  const indices = data?.indices || [
    { symbol: "SPY", price: "439.20", change: "+1.5%", up: true },
    { symbol: "QQQ", price: "388.10", change: "+2.1%", up: true },
    { symbol: "DIA", price: "360.75", change: "+0.8%", up: true },
    { symbol: "IWM", price: "218.50", change: "+1.0%", up: true },
  ];

  // Sector Performance
  const sectors = data?.sectors || [
    { name: "Technology", pct: 35 }, { name: "Financials", pct: 21 },
    { name: "Healthcare", pct: 15 }, { name: "Consumer Disc.", pct: 11 },
    { name: "Others", pct: 18 },
  ];

  // Performance summary table
  const perfTable = data?.performanceTable || [
    { period: "1DAY", returnPct: "1.2%", pnl: "$12,500", sharpe: "2.35", maxDd: " 0.4%", winRatePct: "64.0%", avgWin: "$23.10", avgLoss: "$27.00" },
    { period: "WTD", returnPct: "3.6%", pnl: "$38,100", sharpe: "1.90", maxDd: "-1.5%", winRatePct: "64.5%", avgWin: "$28.10", avgLoss: "$23.00" },
    { period: "MTD", returnPct: "8.5%", pnl: "$43,500", sharpe: "2.53", maxDd: "-2.3%", winRatePct: "65.5%", avgWin: "$27.50", avgLoss: "$22.00" },
    { period: "QTD", returnPct: "10.0%", pnl: "$43,100", sharpe: "1.15", maxDd: "-6.3%", winRatePct: "70.5%", avgWin: "$37.25", avgLoss: "$11.00" },
    { period: "YTD", returnPct: "17.3%", pnl: "$83,000", sharpe: "2.30", maxDd: "-3.1%", winRatePct: "63.1%", avgWin: "$21.50", avgLoss: "$10.00" },
    { period: "INCEPTION", returnPct: "12.4%", pnl: "$65,200", sharpe: "8.45", maxDd: "-5.0%", winRatePct: "70.0%", avgWin: "$73.00", avgLoss: "$10.00" },
  ];

  // ML Insights
  const mlAccuracy = mlData?.accuracy ?? 88.5;
  const mlInsight = mlData?.insight ?? "Market conditions remain favorable for momentum strategies. Risk shield is active. Recommend increasing exposure to technology sector. Potential volatility detected in financials. AI model predicts a positive outlook for Q1 2025.";

  return (
    <div className="space-y-4">
      <PageHeader icon={TrendingUp} title="Embodier Trader - Performance Analytics" subtitle="Real-time portfolio performance, AI insights & risk analysis">
        {error && <span className="text-red-400 text-xs">Failed to load</span>}
        <Button onClick={refetch} className="text-xs"><Download className="w-3 h-3 mr-1" />Export Report</Button>
      </PageHeader>

      {/* === ROW 1: KPI Strip === */}
      <div className="grid grid-cols-8 gap-2">
        {kpis.map((k, i) => {
          const Icon = KPI_ICONS[i % KPI_ICONS.length];
          return (
            <div key={i} onClick={() => {}} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 cursor-pointer hover:bg-slate-700/50 transition-colors">
              <div className="flex items-center gap-1 mb-1">
                <Icon className="w-3 h-3 text-emerald-500" />
                <span className="text-[10px] text-slate-400 truncate">{k.label}</span>
              </div>
              <div className="text-lg font-bold text-white">{k.value}</div>
              <div className="text-[9px] text-slate-500">{k.sub}</div>
            </div>
          );
        })}
      </div>

      {/* === ROW 2: Monthly Heatmap + Equity Curve + Market Overview === */}
      <div className="grid grid-cols-6 gap-3">
        {/* Monthly Returns Heatmap */}
        <div className="col-span-2">
          <Card title="Monthly Returns Heatmap">
            <div className="overflow-x-auto">
              <table className="w-full text-[9px]">
                <thead>
                  <tr>
                    <th className="text-slate-500 text-left p-1">Year</th>
                    {MONTHS.map(m => <th key={m} className="text-slate-500 p-1">{m}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(monthlyReturns).length > 0 ? Object.entries(monthlyReturns).map(([year, vals]) => (
                    <tr key={year}>
                      <td className="text-slate-400 font-medium p-1">{year}</td>
                      {(Array.isArray(vals) ? vals : []).map((v, i) => (
                        <td key={i} className="p-1 text-center">
                          {v !== null && v !== undefined ? (
                            <span className={`px-1 py-0.5 rounded text-[8px] font-medium ${v >= 3 ? "bg-emerald-500/30 text-emerald-300" : v >= 0 ? "bg-emerald-500/15 text-emerald-400" : v >= -1 ? "bg-red-500/15 text-red-400" : "bg-red-500/30 text-red-300"}`}>{v.toFixed(1)}%</span>
                          ) : <span className="text-slate-600">-</span>}
                        </td>
                      ))}
                    </tr>
                  )) : (
                    <tr><td colSpan={13} className="text-center text-slate-500 py-4">No monthly data yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Equity Curve - Lightweight Charts */}
        <div className="col-span-3">
          <Card title="Equity Curve - Lightweight Charts" className="relative">
            <div className="absolute top-2 right-3 flex gap-1">
              {timeframes.map(tf => <button key={tf} onClick={() => setTimeframe(tf)} className={`px-2 py-0.5 text-[10px] rounded cursor-pointer transition-colors ${timeframe === tf ? "bg-primary text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"}`}>{tf}</button>)}
            </div>
            <EquityCurveLC data={equityData?.equityCurve || []} height={220} />
            <div className="mt-1"><DrawdownLC data={equityData?.drawdownCurve || []} height={60} /></div>
          </Card>
        </div>

        {/* Market Overview */}
        <div className="col-span-1">
          <Card title="Market Overview">
            <div className="grid grid-cols-2 gap-2 mb-3">
              {indices.map((idx, i) => (
                <div key={i} className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 cursor-pointer hover:bg-slate-800 transition-colors">
                  <div className="text-xs font-bold text-white">{idx.symbol}</div>
                  <div className="text-sm text-white">{idx.price}</div>
                  <div className={`text-[10px] ${idx.up ? "text-emerald-400" : "text-red-400"}`}>{idx.change}</div>
                </div>
              ))}
            </div>
            <div className="text-[10px] text-slate-400 font-medium mb-1">SECTOR PERFORMANCE</div>
            <div className="space-y-1">
              {sectors.map((s, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-[9px] text-slate-400 w-20 truncate">{s.name}</span>
                  <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-emerald-500/60 rounded-full" style={{ width: `${s.pct}%` }} /></div>
                  <span className="text-[9px] text-slate-400 w-6 text-right">{s.pct}%</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* === ROW 3: SHAP + Consensus + Rolling Sharpe + Factor Decomp + Cumul Returns === */}
      <div className="grid grid-cols-7 gap-3">
        {/* SHAP Feature Importance */}
        <div className="col-span-1">
          <Card title="SHAP Feature Importance">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={shap} layout="vertical" margin={{ left: 50 }}>
                <XAxis type="number" tick={{ fontSize: 8, fill: "#64748b" }} />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 8 }} width={50} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Agent Consensus Donut */}
        <div className="col-span-1">
          <Card title="Agent Consensus">
            <div className="relative" style={{ height: 200 }}>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ zIndex: 10 }}>
                <span className="text-xl font-bold text-white">{consensus[0]?.value || 0}%</span>
                <span className="text-[9px] text-emerald-500 font-bold uppercase tracking-widest">Bull Bias</span>
              </div>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={consensus} innerRadius={45} outerRadius={65} paddingAngle={5} dataKey="value" stroke="none">
                    {consensus.map((_, i) => <Cell key={i} fill={CONSENSUS_COLORS[i % CONSENSUS_COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-3 text-[9px]">
              {consensus.map((c, i) => <span key={i} className="flex items-center gap-1"><div className="w-2 h-2 rounded-full" style={{ background: CONSENSUS_COLORS[i] }} />{c.name}</span>)}
            </div>
          </Card>
        </div>

        {/* Rolling Sharpe */}
        <div className="col-span-2">
          <Card title="Rolling Sharpe">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={rollingSharpe}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" tick={{ fontSize: 8, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 8, fill: "#64748b" }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }} />
                <defs><linearGradient id="shGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.4} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient></defs>
                <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#shGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Factor Decomposition */}
        <div className="col-span-1">
          <Card title="Factor Decomposition">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={factorDecomp} layout="vertical" margin={{ left: 50 }}>
                <XAxis type="number" tick={{ fontSize: 8, fill: "#64748b" }} />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 9 }} width={60} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {factorDecomp.map((d, i) => <Cell key={i} fill={d.value >= 0 ? "#10b981" : "#f43f5e"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Cumulative Returns */}
        <div className="col-span-2">
          <Card title="Cumulative Returns">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={cumulReturns}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" tick={{ fontSize: 8, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 8, fill: "#64748b" }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 9 }} />
                <Line type="monotone" dataKey="strategy" stroke="#10b981" strokeWidth={2} dot={false} name="Strategy" />
                <Line type="monotone" dataKey="spy" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="SPY" />
                <Line type="monotone" dataKey="qqq" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="QQQ" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </div>

      {/* === ROW 4: Brain Map + VaR + Concentration + P&L Distribution === */}
      <div className="grid grid-cols-6 gap-3">
        {/* Swarm Brain Map - ReactFlow */}
        <div className="col-span-3">
          <Card title="Swarm Brain Map - AI Agent Network">
            <SwarmBrainMap data={data?.brainMap} />
          </Card>
        </div>

        {/* VaR Gauge */}
        <div className="col-span-1">
          <Card title="Value at Risk (VaR)">
            <div className="flex flex-col items-center justify-center" style={{ height: 200 }}>
              <div className="relative w-32 h-32">
                <svg viewBox="0 0 120 120" className="w-full h-full">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#1e293b" strokeWidth="10" />
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#f43f5e" strokeWidth="10" strokeDasharray={`${(data?.var99 || 2.5) / 5 * 314} 314`} strokeLinecap="round" transform="rotate(-90 60 60)" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-red-400">-{data?.var99 || "2.5"}%</span>
                  <span className="text-[8px] text-slate-400">99% 1-Day VaR</span>
                </div>
              </div>
              <div className="mt-3 space-y-1 text-[9px] w-full">
                <div className="flex justify-between"><span className="text-slate-400">Beta vs S&P</span><span className="text-white">{data?.beta || "1.15"}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Sortino Ratio</span><span className="text-white">{data?.sortino || "3.21"}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Calmar Ratio</span><span className="text-white">{data?.calmar || "4.05"}</span></div>
              </div>
            </div>
          </Card>
        </div>

        {/* P&L Distribution */}
        <div className="col-span-2">
          <Card title="Trade P&L Distribution">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={tradeDist}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="range" tick={{ fontSize: 7, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 8, fill: "#64748b" }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {tradeDist.map((d, i) => <Cell key={i} fill={parseInt(d.range) >= 0 ? "#10b981" : "#f43f5e"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </div>

      {/* === ROW 5: Performance Table + ML Insights === */}
      <div className="grid grid-cols-6 gap-3">
        {/* Performance Summary Table */}
        <div className="col-span-4">
          <Card title="Performance Summary">
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left text-slate-400 p-2">Period</th>
                    <th className="text-right text-slate-400 p-2">Return</th>
                    <th className="text-right text-slate-400 p-2">P&L</th>
                    <th className="text-right text-slate-400 p-2">Sharpe</th>
                    <th className="text-right text-slate-400 p-2">Max DD</th>
                    <th className="text-right text-slate-400 p-2">Win Rate</th>
                    <th className="text-right text-slate-400 p-2">Avg Win</th>
                    <th className="text-right text-slate-400 p-2">Avg Loss</th>
                  </tr>
                </thead>
                <tbody>
                  {perfTable.map((row, i) => (
                    <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/50 cursor-pointer transition-colors">
                      <td className="p-2 text-white font-medium">{row.period}</td>
                      <td className={`p-2 text-right ${parseFloat(row.returnPct) >= 0 ? "text-emerald-400" : "text-red-400"}`}>{row.returnPct}</td>
                      <td className="p-2 text-right text-white">{row.pnl}</td>
                      <td className="p-2 text-right text-white">{row.sharpe}</td>
                      <td className="p-2 text-right text-red-400">{row.maxDd}</td>
                      <td className="p-2 text-right text-white">{row.winRatePct}</td>
                      <td className="p-2 text-right text-emerald-400">{row.avgWin}</td>
                      <td className="p-2 text-right text-red-400">{row.avgLoss}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* ML Insights */}
        <div className="col-span-2">
          <Card title="ML Insights">
            <div className="flex flex-col items-center mb-4">
              <div className="relative w-24 h-24">
                <svg viewBox="0 0 120 120" className="w-full h-full">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#1e293b" strokeWidth="10" />
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#10b981" strokeWidth="10" strokeDasharray={`${mlAccuracy / 100 * 314} 314`} strokeLinecap="round" transform="rotate(-90 60 60)" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-lg font-bold text-emerald-400">{mlAccuracy}%</span>
                  <span className="text-[8px] text-slate-400">Accuracy</span>
                </div>
              </div>
            </div>
            <div className="text-[10px] text-slate-300 leading-relaxed mb-3">{mlInsight}</div>
            <div className="grid grid-cols-2 gap-2 text-[9px]">
              <div className="bg-slate-800/50 rounded p-2"><span className="text-slate-400">Model</span><br/><span className="text-white font-medium">Ensemble v3.2</span></div>
              <div className="bg-slate-800/50 rounded p-2"><span className="text-slate-400">Updated</span><br/><span className="text-white font-medium">2 min ago</span></div>
              <div className="bg-slate-800/50 rounded p-2"><span className="text-slate-400">Confidence</span><br/><span className="text-emerald-400 font-medium">High</span></div>
              <div className="bg-slate-800/50 rounded p-2"><span className="text-slate-400">Signal</span><br/><span className="text-emerald-400 font-medium">BUY</span></div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
