import React, { useState, useEffect } from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  BarChart, Bar, PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line
} from 'recharts';
import { 
  LayoutDashboard, Activity, Zap, TrendingUp, Shield, Settings, 
  Terminal, Search, Database, Cpu, BarChart3, PieChart as PieChartIcon, 
  ArrowUpRight, ArrowDownRight, RefreshCw, AlertCircle
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- Utility for API Calls ---
const fetchAPI = async (endpoint, fallbackData) => {
  try {
    const response = await fetch(`/api/v1${endpoint}`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.warn(`Failed to fetch ${endpoint}, using fallback data.`, error);
    return fallbackData;
  }
};

// --- Components ---

const Card = ({ title, children, className, action }) => (
  <div className={twMerge("bg-surface rounded-lg p-4 border border-slate-700/50 flex flex-col h-full", className)}>
    <div className="flexjustify-between items-center mb-4">
      <h3 className="text-slate-200 font-medium text-sm uppercase tracking-wider">{title}</h3>
      {action && <div>{action}</div>}
    </div>
    <div className="flex-1 min-h-0 overflow-hidden relative">
      {children}
    </div>
  </div>
);

const SidebarItem = ({ icon: Icon, label, active, onClick }) => (
  <button 
    onClick={onClick}
    className={clsx(
      "w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium",
      active ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
    )}
  >
    <Icon size={18} />
    <span>{label}</span>
  </button>
);

const MetricBadge = ({ label, value, change, isPositive }) => (
  <div className="flex flex-col items-start mr-6 last:mr-0">
    <div className="flex items-center space-x-2">
      <span className="text-slate-400 text-xs font-bold uppercase">{label}</span>
      <span className={clsx("text-xs font-bold", isPositive ? "text-green-400" : "text-red-400")}>
        {change}
      </span>
    </div>
    <span className="text-white text-lg font-mono font-bold">{value}</span>
  </div>
);

// --- Main Dashboard Component ---

export default function EmbodierTrader() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [metrics, setMetrics] = useState({
    spx: { value: "$4280.10", change: "+0.45%", isPositive: true },
    ndaq: { value: "17850.30", change: "-0.12%", isPositive: false },
    dow: { value: "39120.55", change: "+0.33%", isPositive: true },
    btc: { value: "$71500.20", change: "+1.89%", isPositive: true },
    eth: { value: "$3850.40", change: "-0.05%", isPositive: false },
    oil: { value: "$82.30", change: "+0.67%", isPositive: true },
    totalEquity: "$251,450",
    dayPnL: "+$3,520",
    winRate: "69.1%",
    openRisk: "$15,400",
    volatility: "12.5%",
    beta: "1.12",
    alpha: "+4.5%",
    correl: "0.78",
    liquidity: "$50M",
    margin: "25%"
  });

  // Data States
  const [equityData, setEquityData] = useState([]);
  const [drawdownData, setDrawdownData] = useState([]);
  const [winRateData, setWinRateData] = useState([]);
  const [sectorData, setSectorData] = useState([]);
  const [pnlData, setPnlData] = useState([]);
  const [allocationData, setAllocationData] = useState([]);
  const [riskMetrics, setRiskMetrics] = useState([]);
  const [signalAccuracy, setSignalAccuracy] = useState([]);
  const [openClawData, setOpenClawData] = useState([]);
  const [correlationData, setCorrelationData] = useState([]);
  const [agentLeaderboard, setAgentLeaderboard] = useState([]);

  // Fetch Data on Mount
  useEffect(() => {
    const loadData = async () => {
      // Mock Fallbacks matching image data roughly
      const mockEquity = Array.from({ length: 50 }, (_, i) => ({
        date: `2024-01-${i+1}`,
        value: 100000 + Math.random() * 5000 + (i * 1000)
      }));
      setEquityData(await fetchAPI('/performance/equity', mockEquity));

      const mockDrawdown = Array.from({ length: 50 }, (_, i) => ({
        date: `2024-01-${i+1}`,
        value: -Math.abs(Math.random() * 5000)
      }));
      setDrawdownData(await fetchAPI('/performance/drawdown', mockDrawdown));

      const mockWinRate = [
        { name: 'Jan', rate: 45 }, { name: 'Feb', rate: 55 }, { name: 'Mar', rate: 60 },
        { name: 'Apr', rate: 58 }, { name: 'May', rate: 65 }, { name: 'Jun', rate: 70 },
        { name: 'Jul', rate: 68 }, { name: 'Aug', rate: 72 }, { name: 'Sep', rate: 69 },
        { name: 'Oct', rate: 75 }, { name: 'Nov', rate: 78 }, { name: 'Dec', rate: 80 }
      ];
      setWinRateData(await fetchAPI('/performance/win-rate', mockWinRate));

      const mockSector = [
        { name: 'Jan', val: 100 }, { name: 'Feb', val: 120 }, { name: 'Mar', val: 90 },
        { name: 'Apr', val: 140 }, { name: 'May', val: 130 }, { name: 'Jun', val: 80 },
        { name: 'Jul', val: 60 }, { name: 'Aug', val: 110 }, { name: 'Sep', val: 100 },
        { name: 'Oct', val: 150 }, { name: 'Nov', val: 40 }, { name: 'Dec', val: 130 }
      ];
      setSectorData(await fetchAPI('/performance/sectors', mockSector));

      const mockPnl = Array.from({ length: 40 }, (_, i) => ({
        bin: i,
        count: Math.exp(-Math.pow(i - 20, 2) / 50) * 1000
      }));
      setPnlData(await fetchAPI('/performance/pnl-distribution', mockPnl));

      const mockAllocation = [
        { name: 'NVDA', value: 400 }, { name: 'TSLA', value: 300 }, { name: 'AMD', value: 300 },
        { name: 'MSFT', value: 200 }, { name: 'AAPL', value: 200 }, { name: 'META', value: 150 },
        { name: 'GOOGL', value: 100 }, { name: 'CPEX', value: 100 }
      ];
      setAllocationData(await fetchAPI('/portfolio/allocation', mockAllocation));

      const mockRisk = [
        { subject: 'Volatility', A: 120, fullMark: 150 },
        { subject: 'Global Metrics', A: 98, fullMark: 150 },
        { subject: 'Risk Metric', A: 86, fullMark: 150 },
        { subject: 'Slack Metrics', A: 99, fullMark: 150 },
        { subject: 'Stress Points', A: 85, fullMark: 150 },
        { subject: 'Firm Notes', A: 65, fullMark: 150 },
        { subject: 'Raw Metrics', A: 80, fullMark: 150 },
        { subject: 'Beta Tests', A: 90, fullMark: 150 },
      ];
      setRiskMetrics(await fetchAPI('/risk/metrics', mockRisk));

      const mockOpenClaw = [
        { symbol: 'NVDA', equity: '$21,400', pnl: '63,560', alpha: '+0.15', pelf: '+1.06', alpha2: '+0.60', vol: '153.86', res: '$2993.68', liq: '20M', margin: '3.88' },
        { symbol: 'TSLA', equity: '62,000', pnl: '72,10', alpha: '0.60', pelf: '1.00', alpha2: '0.78', vol: '128.25', res: '$523.26', liq: '3.62', margin: '3.62' },
        { symbol: 'AMD', equity: '$21,300', pnl: '460.00', alpha: '+3.00', pelf: '+0.07', alpha2: '-0.60', vol: '12.86', res: '$823.20', liq: '25.00', margin: '25.00' },
        { symbol: 'AAPL', equity: '$20,000', pnl: '$60.00', alpha: '+7.00', pelf: '+3.00', alpha2: '+4.18', vol: '102.65', res: '$3097.29', liq: '23.00', margin: '23.00' },
        { symbol: 'META', equity: '31,000', pnl: '35.00', alpha: '7.63', pelf: '0.00', alpha2: '0.00', vol: '109.56', res: '392.46', liq: '3.00', margin: '3.00' },
      ];
      setOpenClawData(await fetchAPI('/openclaw/candidates', mockOpenClaw));

      const mockLeaderboard = [
        { rank: 1, agent: 'AgileRepo', perf: '101.4%', profit: '$33.84', daypnl: '$49.30', win: '+0.07%' },
        { rank: 2, agent: 'AlphaSnack', perf: '102.5%', profit: '$32.98', daypnl: '$29.20', win: '+0.00%' },
        { rank: 3, agent: 'Aesot', perf: '100.4%', profit: '$27.35', daypnl: '$27.11', win: '+0.08%' },
        { rank: 4, agent: 'GoogullMater', perf: '88.0%', profit: '$33.58', daypnl: '$44.00', win: '+3.00%' },
      ];
      setAgentLeaderboard(await fetchAPI('/agents/leaderboard', mockLeaderboard));

      const mockSignal = Array.from({ length: 30 }, (_, i) => ({
        day: i,
        accuracy: 50 + Math.random() * 50
      }));
      setSignalAccuracy(await fetchAPI('/signals/accuracy', mockSignal));
    };

    loadData();

    // WebSocket Connection
    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onopen = () => console.log('Connected to Embodier Trader WS');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WS Update:', data);
        // Handle real-time updates here (e.g. updating metrics)
      } catch (e) {
        console.error('WS Error', e);
      }
    };

    return () => ws.close();
  }, []);

  const COLORS = ['#0ea5e9', '#10b981', '#f43f5e', '#fbbf24', '#8b5cf6', '#ec4899'];

  return (
    <div className="flex h-screen bg-background text-slate-300 font-sans overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 flex flex-col border-r border-slate-800 bg-surface/50 p-4">
        <div className="flex items-center space-x-3 mb-8 px-2">
          <div className="w-8 h-8 bg-cyan-500 rounded flex items-center justify-center">
            <Activity className="text-white" size={20} />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Embodier Trader</h1>
        </div>

        <div className="space-y-6 overflow-y-auto flex-1">
          <div>
            <h3 className="text-xs font-bold text-primary mb-3 px-4 uppercase tracking-wider">Command</h3>
            <div className="space-y-1">
              <SidebarItem icon={LayoutDashboard} label="Intelligence Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
              <SidebarItem icon={Terminal} label="Agent Command Center" active={activeTab === 'agents'} onClick={() => setActiveTab('agents')} />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold text-primary mb-3 px-4 uppercase tracking-wider">Intelligence</h3>
            <div className="space-y-1">
              <SidebarItem icon={Activity} label="Signal Intelligence" />
              <SidebarItem icon={Zap} label="Sentiment Intelligence" />
              <SidebarItem icon={Database} label="Data Sources Monitor" />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold text-primary mb-3 px-4 uppercase tracking-wider">ML & Analysis</h3>
            <div className="space-y-1">
              <SidebarItem icon={Cpu} label="ML Brain & Flywheel" />
              <SidebarItem icon={Search} label="Screener & Patterns" />
              <SidebarItem icon={BarChart3} label="Backtesting Lab" />
              <SidebarItem icon={TrendingUp} label="Performance Analytics" />
              <SidebarItem icon={PieChartIcon} label="Market Regime" />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold text-primary mb-3 px-4 uppercase tracking-wider">Execution</h3>
            <div className="space-y-1">
              <SidebarItem icon={ArrowUpRight} label="Active Trades" />
              <SidebarItem icon={Shield} label="Risk Intelligence" />
              <SidebarItem icon={ArrowDownRight} label="Trade Execution" />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold text-primary mb-3 px-4 uppercase tracking-wider">System</h3>
            <div className="space-y-1">
              <SidebarItem icon={Settings} label="Settings" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header Metrics */}
        <div className="h-16 border-b border-slate-800 bg-surface/30 flex items-center px-6 overflow-x-auto whitespace-nowrap">
          <MetricBadge label="SPX" value={metrics.spx.value} change={metrics.spx.change} isPositive={metrics.spx.isPositive} />
          <MetricBadge label="NDAQ" value={metrics.ndaq.value} change={metrics.ndaq.change} isPositive={metrics.ndaq.isPositive} />
          <MetricBadge label="DOW" value={metrics.dow.value} change={metrics.dow.change} isPositive={metrics.dow.isPositive} />
          <MetricBadge label="BTC" value={metrics.btc.value} change={metrics.btc.change} isPositive={metrics.btc.isPositive} />
          <MetricBadge label="ETH" value={metrics.eth.value} change={metrics.eth.change} isPositive={metrics.eth.isPositive} />
          <div className="h-8 w-px bg-slate-700 mx-4"></div>
          <MetricBadge label="Total Equity" value={metrics.totalEquity} change="" isPositive={true} />
          <MetricBadge label="Day P&L" value={metrics.dayPnL} change={metrics.dayPnL} isPositive={metrics.dayPnL.startsWith('+')} />
          <MetricBadge label="Win Rate" value={metrics.winRate} change="" isPositive={true} />
        </div>

        {/* Dashboard Grid */}
        <div className="flex-1 overflow-y-auto p-6 bg-background">
          <div className="grid grid-cols-12 gap-6 pb-6">
            
            {/* Row 1 */}
            <div className="col-span-3 h-64">
              <Card title="Equity Curve" action={<span className="text-xs bg-green-900 text-green-400 px-2 py-1 rounded">YTD +10.3%</span>}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityData}>
                    <defs>
                      <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="date" hide />
                    <YAxis hide domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                    <Area type="monotone" dataKey="value" stroke="#0ea5e9" fillOpacity={1} fill="url(#colorEquity)" />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
            </div>
            <div className="col-span-3 h-64">
              <Card title="Drawdown Chart">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={drawdownData}>
                    <defs>
                      <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="date" hide />
                    <YAxis hide />
                    <Tooltip contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                    <Area type="monotone" dataKey="value" stroke="#f43f5e" fillOpacity={1} fill="url(#colorDrawdown)" />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
            </div>
            <div className="col-span-3 h-64">
              <Card title="Win Rate Over Time">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={winRateData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="name" tick={{fill: '#64748b', fontSize: 10}} />
                    <YAxis hide />
                    <Tooltip cursor={{fill: 'transparent'}} contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                    <Bar dataKey="rate" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>
            <div className="col-span-3 h-64">
              <Card title="Sector Performance">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sectorData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="name" tick={{fill: '#64748b', fontSize: 10}} />
                    <YAxis hide />
                    <Tooltip cursor={{fill: 'transparent'}} contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                    <Bar dataKey="val" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>

            {/* Row 2: P&L Distribution */}
            <div className="col-span-12 h-64">
              <Card title="P&L Distribution">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={pnlData} barCategoryGap={1}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="bin" tick={{fill: '#64748b', fontSize: 10}} />
                    <Tooltip cursor={{fill: 'transparent'}} contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                    <Bar dataKey="count" fill="#0ea5e9" radius={[2, 2, 0, 0]}>
                      {pnlData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index > 20 ? '#10b981' : '#0ea5e9'} /> // Green for right tail
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>

            {/* Row 3 */}
            <div className="col-span-4 h-96">
              <Card title="OpenClaw Candidates" action={<span className="text-xs bg-slate-700 px-2 py-1 rounded">YTD -16.2%</span>}>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-400">
                    <thead className="text-slate-500 font-medium border-b border-slate-700">
                      <tr>
                        <th className="pb-2">Share</th>
                        <th className="pb-2">Equity</th>
                        <th className="pb-2">P&L</th>
                        <th className="pb-2">Alpha</th>
                        <th className="pb-2">Vol</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {openClawData.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-800/50">
                          <td className="py-2 text-white font-medium">{row.symbol}</td>
                          <td className="py-2">{row.equity}</td>
                          <td className="py-2 text-green-400">{row.pnl}</td>
                          <td className="py-2 text-green-400">{row.alpha}</td>
                          <td className="py-2">{row.vol}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>

            <div className="col-span-4 h-96">
              <Card title="Portfolio Allocation">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={allocationData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      fill="#8884d8"
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {allocationData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  {allocationData.slice(0, 6).map((item, i) => (
                    <div key={i} className="flex items-center text-xs text-slate-400">
                      <span className="w-2 h-2 rounded-full mr-2" style={{backgroundColor: COLORS[i % COLORS.length]}}></span>
                      {item.name}
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="col-span-4 h-96">
              <Card title="Risk Metrics">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={riskMetrics}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis dataKey="subject" tick={{fill: '#94a3b8', fontSize: 10}} />
                    <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                    <Radar name="Portfolio" dataKey="A" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
                    <Tooltip contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                  </RadarChart>
                </ResponsiveContainer>
              </Card>
            </div>

            {/* Row 4 */}
            <div className="col-span-6 h-80">
              <Card title="Correlation Matrix">
                 {/* Simplified Heatmap Grid */}
                 <div className="grid grid-cols-10 gap-1 text-[8px] text-center text-slate-400">
                    <div className="col-span-1"></div>
                    {['NVDA','TSLA','AMD','MSFT','AAPL','NFLX','CRM','DIS','V'].map(t => <div key={t}>{t}</div>)}
                    {['NVDA','TSLA','AMD','MSFT','AAPL','NFLX','CRM','DIS','V'].map((row, rI) => (
                      <React.Fragment key={row}>
                        <div className="col-span-1 font-bold">{row}</div>
                        {Array.from({length: 9}).map((_, cI) => {
                          const val = rI === cI ? 1.0 : Math.random().toFixed(2);
                          const bg = val > 0.7 ? 'bg-green-500/80 text-black' : val > 0.3 ? 'bg-green-500/30' : 'bg-slate-800';
                          return <div key={cI} className={`p-1 rounded ${bg}`}>{val}</div>
                        })}
                      </React.Fragment>
                    ))}
                 </div>
              </Card>
            </div>

            <div className="col-span-3 h-80">
              <Card title="Agent Performance Leaderboard">
                <table className="w-full text-left text-xs text-slate-400">
                    <thead className="text-slate-500 font-medium border-b border-slate-700">
                      <tr>
                        <th className="pb-2">Agent</th>
                        <th className="pb-2">Perf</th>
                        <th className="pb-2">Day P&L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {agentLeaderboard.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-800/50">
                          <td className="py-2 text-white font-medium flex items-center">
                            <span className="mr-2 text-slate-500">{row.rank}</span>
                            {row.agent}
                          </td>
                          <td className="py-2 text-green-400">{row.perf}</td>
                          <td className="py-2 text-green-400">{row.daypnl}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
              </Card>
            </div>

            <div className="col-span-3 h-80">
              <Card title="Signal Accuracy Timeline">
                <ResponsiveContainer width="100%" height="100%">
                   <BarChart data={signalAccuracy}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="day" hide />
                    <Tooltip cursor={{fill: 'transparent'}} contentStyle={{backgroundColor: '#1e293b', border: 'none'}} />
                    <Bar dataKey="accuracy" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}