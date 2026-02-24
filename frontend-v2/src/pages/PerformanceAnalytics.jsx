// PERFORMANCE ANALYTICS - Embodier.ai Glass House Intelligence System
// GET /api/v1/performance - market stats, summary, monthly returns, factors
import { useState } from "react";
import { Download, TrendingUp, TrendingDown } from "lucide-react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function MarketStat({ label, value, change, sub, up }) {
  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl p-4">
      <div className="text-xs text-secondary mb-1">{label}</div>
      <div className="text-xl font-bold text-white">{value}</div>
      {change && (
        <div
          className={`flex items-center gap-1 text-xs mt-1 ${up ? "text-success" : "text-danger"}`}
        >
          {up ? (
            <TrendingUp className="w-3 h-3" />
          ) : (
            <TrendingDown className="w-3 h-3" />
          )}
          {change}
        </div>
      )}
      {sub && (
        <div
          className={`text-xs mt-1 ${up ? "text-emerald-400" : "text-gray-400"}`}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

export default function PerformanceAnalytics() {
  const [timeframe, setTimeframe] = useState("1W");
  const timeframes = ["1H", "4H", "1D", "1W", "1M", "1Y", "ALL"];
  const { data, loading, error, refetch } = useApi("performance", {
    pollIntervalMs: 60000,
  });
  const marketStats = Array.isArray(data?.marketStats) ? data.marketStats : [];
  const summary = Array.isArray(data?.summary) ? data.summary : [];
  const monthlyReturns = data?.monthlyReturns ?? {};
  const factors = Array.isArray(data?.factors) ? data.factors : [];
  const portfolioValue = data?.portfolioValue ?? null;
  const dailyPnL = data?.dailyPnL ?? null;
  const dailyPnLPct = data?.dailyPnLPct ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        icon={TrendingUp}
        title="Performance Analytics"
        description={error ? "Failed to load" : "Portfolio and market performance"}
      >
        {error && (
          <span className="text-xs font-medium text-danger">
            Failed to load
          </span>
        )}
        <Button variant="primary" leftIcon={Download}>
          Export Report
        </Button>
      </PageHeader>

      {loading && marketStats.length === 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4 animate-pulse"
            >
              <div className="h-3 bg-secondary/20 rounded w-2/3 mb-2" />
              <div className="h-6 bg-secondary/20 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}
      {error && marketStats.length === 0 && (
        <Card className="p-6 text-center">
          <p className="text-secondary mb-2">
            Could not load performance. Check GET /api/v1/performance.
          </p>
          <Button variant="outline" size="sm" onClick={refetch}>
            Retry
          </Button>
        </Card>
      )}
      {!loading && !error && (portfolioValue != null || dailyPnL != null) && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {portfolioValue != null && (
            <div className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4">
              <div className="text-xs font-medium uppercase tracking-wider text-secondary">Portfolio Value</div>
              <div className="mt-1 text-xl font-bold text-white">
                ${Number(portfolioValue).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </div>
            </div>
          )}
          {dailyPnL != null && (
            <div className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4">
              <div className="text-xs font-medium uppercase tracking-wider text-secondary">Daily P&L</div>
              <div className={`mt-1 text-xl font-bold ${dailyPnL >= 0 ? "text-success" : "text-danger"}`}>
                {dailyPnL >= 0 ? "+" : ""}${Number(dailyPnL).toFixed(2)}
              </div>
              {dailyPnLPct != null && (
                <div className={`text-xs mt-0.5 ${dailyPnLPct >= 0 ? "text-success" : "text-danger"}`}>
                  {dailyPnLPct >= 0 ? "+" : ""}{Number(dailyPnLPct).toFixed(2)}%
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {!loading && marketStats.length > 0 && (
        <>
          {/* Market Overview */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-3">
              Market Overview
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {marketStats.map((s, i) => (
                <MarketStat key={i} {...s} />
              ))}
            </div>
          </div>

          {/* Performance Summary */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-3">
              Performance Summary
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {summary.map((s, i) => (
                <div
                  key={i}
                  className="bg-slate-900/40 border border-white/5 rounded-xl p-4"
                >
                  <div className="text-xs text-gray-500 mb-1">{s.label}</div>
                  <div className="text-2xl font-bold text-white">{s.value}</div>
                  <div
                    className={`flex items-center gap-1 text-xs mt-1 ${s.up ? "text-emerald-400" : "text-red-400"}`}
                  >
                    {s.up ? (
                      <TrendingUp className="w-3 h-3" />
                    ) : (
                      <TrendingDown className="w-3 h-3" />
                    )}
                    {s.sub}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Card title="Portfolio Performance">
            <div className="flex justify-end gap-1 mb-4 -mt-1">
              {timeframes.map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    timeframe === tf
                      ? "bg-primary text-white"
                      : "text-secondary hover:text-white hover:bg-secondary/20"
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
            <div className="h-48 bg-dark/50 rounded-xl border border-secondary/50 flex items-end px-4 pb-4 gap-1">
              {[
                30, 32, 35, 33, 38, 40, 42, 45, 44, 48, 50, 52, 55, 58, 56, 60,
                62, 65, 68, 72, 75, 78, 80, 85,
              ].map((v, i) => (
                <div
                  key={i}
                  className="flex-1 bg-gradient-to-t from-primary to-primary/70 rounded-t opacity-80"
                  style={{ height: `${v}%` }}
                />
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="Monthly Returns Heatmap (2023-2024)">
              <p className="text-xs text-secondary mb-4">
                Color intensity indicates monthly performance.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="text-left text-xs text-gray-500 pb-2"></th>
                      {MONTHS.map((m) => (
                        <th
                          key={m}
                          className="text-center text-xs text-gray-500 pb-2 px-1"
                        >
                          {m}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(monthlyReturns).map(([year, vals]) => (
                      <tr key={year}>
                        <td className="text-sm text-gray-400 pr-3 py-1">
                          {year}
                        </td>
                        {vals.map((v, i) => (
                          <td key={i} className="text-center py-1 px-1">
                            {v !== null ? (
                              <span
                                className={`inline-block w-full px-1 py-0.5 rounded text-xs font-medium ${
                                  v >= 3
                                    ? "bg-emerald-500/30 text-emerald-300"
                                    : v >= 0
                                      ? "bg-emerald-500/15 text-emerald-400"
                                      : v >= -1
                                        ? "bg-red-500/15 text-red-400"
                                        : "bg-red-500/30 text-red-300"
                                }`}
                              >
                                {v.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-xs text-gray-700">-</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card title="Returns Decomposition">
              <p className="text-xs text-secondary mb-4">
                Breakdown of portfolio returns by factor.
              </p>
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-secondary uppercase">
                    <th className="text-left pb-3">Factor</th>
                    <th className="text-right pb-3">Contribution</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary/30">
                  {factors.map((f, i) => (
                    <tr
                      key={i}
                      className="hover:bg-secondary/5 transition-colors"
                    >
                      <td className="py-3 text-sm text-white">{f.name}</td>
                      <td
                        className={`py-3 text-sm font-medium text-right ${f.up ? "text-success" : "text-danger"}`}
                      >
                        {f.value}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="ML Insights">
              <div className="space-y-3">
                <button className="flex items-center gap-2 text-sm text-primary hover:text-primary/80">
                  View Details
                </button>
                <p className="text-sm text-white leading-relaxed">
                  Our machine learning models predict a moderate uptrend for
                  growth stocks in the next quarter, driven by expected interest
                  rate stability. Specific sectors to watch include renewable
                  energy and AI infrastructure. Consider tactical allocations to
                  these areas for potential outperformance.
                </p>
                <p className="text-xs text-secondary mt-2">
                  Prediction accuracy: 78% for the next 30 days. Model last
                  updated: 2024-07-20.
                </p>
              </div>
            </Card>

            <Card title="Risk Shield Summary">
              <div className="space-y-3">
                <button className="flex items-center gap-2 text-sm text-primary hover:text-primary/80">
                  View Details
                </button>
                <ul className="space-y-2 text-sm text-white">
                  <li className="flex items-start gap-2">
                    <span className="text-secondary">-</span>Total Portfolio VaR
                    (99%, 1-day): -2.5%
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-secondary">-</span>Current Beta vs.
                    S&P 500: 1.15 (slightly aggressive)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-secondary">-</span>Concentration Risk
                    (Top 5 Holdings): 35%
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-secondary">-</span>Liquidity Profile:
                    High. Majority of holdings are highly liquid.
                  </li>
                </ul>
                <p className="text-sm text-secondary mt-2">
                  Recommendations: Diversify exposure in technology sector to
                  mitigate concentration risk.
                </p>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
