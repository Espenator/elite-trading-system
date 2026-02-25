"use client";

import React, { useState, useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import { ShieldAlert, TrendingUp, AlertTriangle, Activity, BarChart2, CheckCircle, AlertOctagon } from 'lucide-react';

// --- Lightweight Chart Component for VIX/RSI ---
const VixRegimeChart = ({ data }) => {
  const chartContainerRef = useRef();

  useEffect(() => {
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(51, 65, 85, 0.3)' },
        horzLines: { color: 'rgba(51, 65, 85, 0.3)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 350,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const vixSeries = chart.addLineSeries({
      color: '#ef4444',
      lineWidth: 2,
      title: 'VIX Level',
    });

    vixSeries.setData(data.vix);

    // Add Regime Threshold Lines
    vixSeries.createPriceLine({
      price: 30,
      color: '#ef4444',
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: 'RED ZONE (>30)',
    });
    
    vixSeries.createPriceLine({
      price: 20,
      color: '#eab308',
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: 'YELLOW ZONE (>20)',
    });

    chart.timeScale().fitContent();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
};

// --- Main Dashboard Component ---
export default function MarketRegime() {
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [regimeState, setRegimeState] = useState({
    status: 'YELLOW',
    vix: 24.5,
    vixRsi: 48,
    breadth: 0.42,
    hySpread: 450,
  });

  // Mocked VIX data for the chart initialization
  const mockVixData = {
    vix: Array.from({ length: 100 }, (_, i) => ({
      time: new Date(Date.now() - (100 - i) * 86400000).toISOString().split('T')[0],
      value: 15 + Math.sin(i * 0.1) * 10 + Math.random() * 5
    }))
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-blue-950 to-slate-950 text-slate-200 p-6">
      
      {/* Header */}
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
            <Activity className="w-10 h-10 text-blue-500" />
            Market Regime Intelligence
          </h1>
          <p className="text-slate-400">Automated classification for System 1-5 allocation.</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-slate-400 mb-1">System Status</p>
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span className="text-sm font-semibold text-white">LIVE: Monitoring Flow</span>
          </div>
        </div>
      </div>

      {/* KPI Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        
        {/* Regime Status Card */}
        <div className={`p-6 rounded-xl border backdrop-blur-sm shadow-xl transition-all ${
          regimeState.status === 'GREEN' ? 'bg-green-900/20 border-green-500/50 shadow-green-500/10' :
          regimeState.status === 'YELLOW' ? 'bg-yellow-900/20 border-yellow-500/50 shadow-yellow-500/10' :
          'bg-red-900/20 border-red-500/50 shadow-red-500/10'
        }`}>
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-slate-400 font-semibold">CURRENT REGIME</p>
            <ShieldAlert className={`w-5 h-5 ${regimeState.status === 'YELLOW' ? 'text-yellow-500' : 'text-slate-400'}`} />
          </div>
          <h2 className={`text-3xl font-bold mb-2 ${
            regimeState.status === 'YELLOW' ? 'text-yellow-500' : 'text-white'
          }`}>{regimeState.status}</h2>
          <p className="text-xs text-slate-400">40% Momentum / 60% Reversion</p>
        </div>

        {/* VIX Level Card */}
        <div className="bg-slate-800/50 border border-slate-700/50 p-6 rounded-xl backdrop-blur-sm hover:border-slate-600/50 transition-all">
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-slate-400 font-semibold">CBOE VIX</p>
            <TrendingUp className="w-5 h-5 text-slate-400" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">{regimeState.vix.toFixed(2)}</h2>
          <p className="text-xs text-yellow-400">Elevated Volatility</p>
        </div>

        {/* HY Spread Card */}
        <div className="bg-slate-800/50 border border-slate-700/50 p-6 rounded-xl backdrop-blur-sm hover:border-slate-600/50 transition-all">
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-slate-400 font-semibold">HY SPREAD (HYG-IEF)</p>
            <AlertTriangle className="w-5 h-5 text-slate-400" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">{regimeState.hySpread} bps</h2>
          <p className="text-xs text-slate-400">Normal (Limit: 700 bps)</p>
        </div>

        {/* Market Breadth */}
        <div className="bg-slate-800/50 border border-slate-700/50 p-6 rounded-xl backdrop-blur-sm hover:border-slate-600/50 transition-all">
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-slate-400 font-semibold">BREADTH (Adv/Dec)</p>
            <BarChart2 className="w-5 h-5 text-slate-400" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">{regimeState.breadth.toFixed(2)}</h2>
          <p className="text-xs text-slate-400">Weakness Detected</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* VIX Lightweight Chart */}
        <div className="lg:col-span-2 bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            VIX vs Regime Thresholds
          </h3>
          <div className="h-[350px] w-full">
            <VixRegimeChart data={mockVixData} />
          </div>
        </div>

        {/* Action Plan & Crash Protocol */}
        <div className="space-y-6">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-blue-400" />
              Today's Action Plan
            </h3>
            <ul className="space-y-3">
              <li className="flex justify-between items-center text-sm border-b border-slate-700/50 pb-2">
                <span className="text-slate-400">Risk Per Trade</span>
                <span className="font-bold text-white">1.5%</span>
              </li>
              <li className="flex justify-between items-center text-sm border-b border-slate-700/50 pb-2">
                <span className="text-slate-400">Max Positions</span>
                <span className="font-bold text-white">5</span>
              </li>
              <li className="flex justify-between items-center text-sm border-b border-slate-700/50 pb-2">
                <span className="text-slate-400">Active Systems</span>
                <span className="font-bold text-white">All 5 Systems</span>
              </li>
              <li className="flex justify-between items-center text-sm pt-1">
                <span className="text-slate-400">Strategy Mix</span>
                <span className="font-bold text-yellow-400">40% Mom / 60% Rev</span>
              </li>
            </ul>
          </div>

          {/* Crash Protocol Widget */}
          <div className="bg-red-950/30 border border-red-900/50 rounded-xl p-6 backdrop-blur-sm">
            <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
              <AlertOctagon className="w-5 h-5" />
              Crash Protocol Watch
            </h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">HY Spread Limit (700bps)</span>
                  <span className="text-white">450 / 700</span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: '64%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">VIX Daily Limit (40.0)</span>
                  <span className="text-white">24.5 / 40.0</span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-2">
                  <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '61%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Rules Matrix Table */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm">
        <div className="p-4 border-b border-slate-700/50 bg-slate-900/30">
          <h3 className="text-lg font-bold text-white">Regime Decision Matrix</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-400 bg-slate-900/50 uppercase">
              <tr>
                <th className="px-6 py-4">Regime</th>
                <th className="px-6 py-4">VIX Level</th>
                <th className="px-6 py-4">Strategy Mix</th>
                <th className="px-6 py-4">Risk / Trade</th>
                <th className="px-6 py-4">Max Pos</th>
                <th className="px-6 py-4">Active Systems</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              <tr className="hover:bg-slate-700/20 transition-colors">
                <td className="px-6 py-4 font-bold text-green-400">GREEN</td>
                <td className="px-6 py-4 text-slate-300">&lt; 20.0</td>
                <td className="px-6 py-4 text-slate-300">70% Momentum / 30% Reversion</td>
                <td className="px-6 py-4 text-slate-300">2.0%</td>
                <td className="px-6 py-4 text-slate-300">6</td>
                <td className="px-6 py-4 text-slate-300">All 5 Systems</td>
              </tr>
              <tr className="bg-yellow-900/10 hover:bg-slate-700/20 transition-colors">
                <td className="px-6 py-4 font-bold text-yellow-400">YELLOW (Active)</td>
                <td className="px-6 py-4 text-slate-300">20.0 - 30.0</td>
                <td className="px-6 py-4 text-slate-300">40% Momentum / 60% Reversion</td>
                <td className="px-6 py-4 text-slate-300">1.5%</td>
                <td className="px-6 py-4 text-slate-300">5</td>
                <td className="px-6 py-4 text-slate-300">All 5 Systems</td>
              </tr>
              <tr className="hover:bg-slate-700/20 transition-colors">
                <td className="px-6 py-4 font-bold text-red-500">RED</td>
                <td className="px-6 py-4 text-slate-300">&gt; 30.0 (RSI &lt; 40)</td>
                <td className="px-6 py-4 text-slate-300">0% Momentum / 0% Reversion</td>
                <td className="px-6 py-4 text-slate-300">0.0%</td>
                <td className="px-6 py-4 text-slate-300">0</td>
                <td className="px-6 py-4 text-slate-300">CASH ONLY</td>
              </tr>
              <tr className="hover:bg-slate-700/20 transition-colors">
                <td className="px-6 py-4 font-bold text-orange-400">RED RECOVERY</td>
                <td className="px-6 py-4 text-slate-300">&gt; 30.0 (RSI &gt; 40)</td>
                <td className="px-6 py-4 text-slate-300">0% Momentum / 100% Reversion</td>
                <td className="px-6 py-4 text-slate-300">1.0%</td>
                <td className="px-6 py-4 text-slate-300">4</td>
                <td className="px-6 py-4 text-slate-300">System 5 ONLY</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
