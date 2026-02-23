# OLEH HANDOFF - Agent Command Center + Full Wiring Instructions

**From:** Espen (via AI architecture review)  
**Date:** Monday Feb 23, 2026  
**Priority:** 🚨 Read this FIRST before starting any work

---

## 🎯 TL;DR: Build the Agent Command Center

The OpenClaw backend bridge is **COMPLETE** (11 endpoints, Gist polling, 15min cache). Your mission this week: **transform the Embodier Trader frontend into an Agent Command Center** - a glass-box dashboard where Espen sees EVERYTHING the OpenClaw agents see in real-time.

---

## ✅ BACKEND STATUS: COMPLETE

### Files Already Committed to v2

| File | Status | Description |
|------|--------|-------------|
| `services/openclaw_bridge_service.py` | ✅ DONE | Gist polling, 15min cache, typed accessors |
| `api/v1/openclaw.py` | ✅ DONE | 11 endpoints: /scan, /regime, /top, /health, /whale-flow, /fom, /llm, /sectors, /memory, /memory/recall, /refresh |
| `core/config.py` | ✅ DONE | OPENCLAW_GIST_ID + OPENCLAW_GIST_TOKEN |
| `main.py` | ✅ DONE | Router registered at /api/v1/openclaw |
| `services/market_data_agent.py` | ✅ DONE | OpenClaw as 6th data source |
| `services/signal_engine.py` | ✅ DONE | 60/40 blending + regime multipliers |

### Test the Bridge (Monday First Thing)

```bash
# 1. Pull latest v2
git checkout v2 && git pull

# 2. Add to .env
OPENCLAW_GIST_ID=your_gist_id_here
OPENCLAW_GIST_TOKEN=ghp_your_token_here

# 3. Start backend
cd backend && python -m uvicorn app.main:app --port 8001 --reload

# 4. Test endpoints
curl http://localhost:8001/api/v1/openclaw/health
curl http://localhost:8001/api/v1/openclaw/regime
curl http://localhost:8001/api/v1/openclaw/top?n=5
```

---

## 🏗️ AGENT COMMAND CENTER: Frontend Components

### Component Architecture

```
App.jsx
├── Header.jsx
│   └── RegimeBanner.jsx (NEW - always visible regime status)
├── Sidebar.jsx
├── Dashboard.jsx
│   ├── RegimeCard.jsx (NEW - detailed regime info)
│   ├── TopCandidatesCard.jsx (NEW - top 5 from OpenClaw)
│   └── BridgeHealthCard.jsx (NEW - OpenClaw connection status)
├── ClawBotPanel.jsx (NEW PAGE - main command center)
│   ├── LiveScoresTable.jsx (NEW - all candidates sortable)
│   ├── WhaleFlowPanel.jsx (NEW - unusual options)
│   ├── LLMSummaryCard.jsx (NEW - AI analysis)
│   └── FOMExpectedMoves.jsx (NEW - options levels)
├── AgentCommandCenter.jsx (ENHANCE - agent status)
│   ├── AgentSwarmPanel.jsx (NEW - heartbeat status)
│   └── BlackboardViewer.jsx (NEW - message feed)
└── Signals.jsx (ENHANCE - add OpenClaw columns)
```

---

## 📅 WEEK 1 TASKS: Daily Breakdown

### DAY 1 (Monday Feb 24) - Dashboard + Regime Banner
**Time: 5-6 hours**

#### Task 1.1: RegimeBanner.jsx (Header - Always Visible)
```jsx
// frontend-v2/src/components/layout/RegimeBanner.jsx
import { useEffect, useState } from 'react';
import { api } from '../../services/api';

export default function RegimeBanner() {
  const [regime, setRegime] = useState({ state: 'LOADING' });
  
  useEffect(() => {
    const fetchRegime = async () => {
      try {
        const res = await api.get('/api/v1/openclaw/regime');
        setRegime(res.data);
      } catch (err) {
        setRegime({ state: 'ERROR', error: err.message });
      }
    };
    fetchRegime();
    const interval = setInterval(fetchRegime, 60000); // 1 min refresh
    return () => clearInterval(interval);
  }, []);

  const colors = {
    GREEN: 'bg-green-500',
    YELLOW: 'bg-yellow-500',
    RED: 'bg-red-500',
    LOADING: 'bg-gray-500',
    ERROR: 'bg-gray-700'
  };

  return (
    <div className={`${colors[regime.state]} text-white px-4 py-2 flex items-center justify-between`}>
      <div className="flex items-center gap-4">
        <span className="font-bold text-lg">🦖 {regime.state}</span>
        {regime.vix && <span>VIX: {regime.vix?.toFixed(1)}</span>}
        {regime.hmm_confidence && <span>HMM: {(regime.hmm_confidence * 100).toFixed(0)}%</span>}
        {regime.hurst && <span>Hurst: {regime.hurst?.toFixed(2)}</span>}
      </div>
      {regime.scan_date && (
        <span className="text-sm opacity-75">Scan: {regime.scan_date}</span>
      )}
    </div>
  );
}
```

**Wire into Header.jsx:**
```jsx
// Add to Header.jsx
import RegimeBanner from './RegimeBanner';
// ...
return (
  <>
    <RegimeBanner />
    <header className="...">...</header>
  </>
);
```

#### Task 1.2: Dashboard OpenClaw Cards

**RegimeCard.jsx:**
```jsx
// frontend-v2/src/components/dashboard/RegimeCard.jsx
export default function RegimeCard({ regime }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-2">🌊 Market Regime</h3>
      <div className="grid grid-cols-2 gap-2">
        <div>State: <span className="font-bold">{regime?.state}</span></div>
        <div>VIX: {regime?.vix?.toFixed(1)}</div>
        <div>HMM Confidence: {(regime?.hmm_confidence * 100)?.toFixed(0)}%</div>
        <div>Hurst: {regime?.hurst?.toFixed(2)}</div>
      </div>
      {regime?.readme && (
        <p className="mt-2 text-sm text-gray-400">{regime.readme}</p>
      )}
    </div>
  );
}
```

**TopCandidatesCard.jsx:**
```jsx
// frontend-v2/src/components/dashboard/TopCandidatesCard.jsx
export default function TopCandidatesCard({ candidates }) {
  const tierColors = {
    SLAM: 'text-yellow-400',
    HIGH: 'text-green-400',
    TRADEABLE: 'text-blue-400',
    WATCH: 'text-gray-400'
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-2">🦖 Top OpenClaw Candidates</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400">
            <th className="text-left">Symbol</th>
            <th className="text-right">Score</th>
            <th className="text-center">Tier</th>
            <th className="text-right">Entry</th>
          </tr>
        </thead>
        <tbody>
          {candidates?.slice(0, 5).map(c => (
            <tr key={c.symbol} className="border-t border-slate-700">
              <td className="font-mono font-bold">{c.symbol}</td>
              <td className="text-right">{c.composite_score?.toFixed(1)}</td>
              <td className={`text-center ${tierColors[c.tier]}`}>{c.tier}</td>
              <td className="text-right">${c.suggested_entry?.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Update Dashboard.jsx:**
```jsx
// Add to Dashboard.jsx
import { useEffect, useState } from 'react';
import { api } from '../services/api';
import RegimeCard from '../components/dashboard/RegimeCard';
import TopCandidatesCard from '../components/dashboard/TopCandidatesCard';

export default function Dashboard() {
  const [regime, setRegime] = useState(null);
  const [topCandidates, setTopCandidates] = useState([]);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const fetchOpenClawData = async () => {
      try {
        const [regimeRes, topRes, healthRes] = await Promise.all([
          api.get('/api/v1/openclaw/regime'),
          api.get('/api/v1/openclaw/top?n=5'),
          api.get('/api/v1/openclaw/health')
        ]);
        setRegime(regimeRes.data);
        setTopCandidates(topRes.data.candidates || []);
        setHealth(healthRes.data);
      } catch (err) {
        console.error('OpenClaw fetch failed:', err);
      }
    };
    fetchOpenClawData();
    const interval = setInterval(fetchOpenClawData, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Agent Command Center</h1>
      
      {/* OpenClaw Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <RegimeCard regime={regime} />
        <TopCandidatesCard candidates={topCandidates} />
        <div className="bg-slate-800 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-2">📶 Bridge Health</h3>
          <div className="space-y-1 text-sm">
            <div>Connected: {health?.connected ? '✅' : '❌'}</div>
            <div>Candidates: {health?.candidate_count}</div>
            <div>Cache Age: {health?.cache_age_seconds?.toFixed(0)}s</div>
            <div>Last Scan: {health?.last_scan_timestamp}</div>
          </div>
        </div>
      </div>
      
      {/* Rest of existing dashboard */}
    </div>
  );
}
```

---

### DAY 2 (Tuesday Feb 25) - ClawBotPanel.jsx (New Page)
**Time: 5-6 hours**

#### Task 2.1: Create ClawBotPanel.jsx

```jsx
// frontend-v2/src/pages/ClawBotPanel.jsx
import { useEffect, useState } from 'react';
import { api } from '../services/api';

export default function ClawBotPanel() {
  const [data, setData] = useState({
    regime: null,
    candidates: [],
    whaleFlow: [],
    llm: null,
    fom: {}
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [regimeRes, topRes, whaleRes, llmRes, fomRes] = await Promise.all([
          api.get('/api/v1/openclaw/regime'),
          api.get('/api/v1/openclaw/top?n=20'),
          api.get('/api/v1/openclaw/whale-flow'),
          api.get('/api/v1/openclaw/llm'),
          api.get('/api/v1/openclaw/fom')
        ]);
        setData({
          regime: regimeRes.data,
          candidates: topRes.data.candidates || [],
          whaleFlow: whaleRes.data.alerts || [],
          llm: llmRes.data,
          fom: fomRes.data
        });
      } catch (err) {
        console.error('ClawBot fetch failed:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
    const interval = setInterval(fetchAll, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setLoading(true);
    await api.post('/api/v1/openclaw/refresh');
    window.location.reload();
  };

  const tierBadge = (tier) => {
    const styles = {
      SLAM: 'bg-yellow-500 text-black',
      HIGH: 'bg-green-500 text-white',
      TRADEABLE: 'bg-blue-500 text-white',
      WATCH: 'bg-gray-500 text-white',
      NO_DATA: 'bg-gray-700 text-gray-400'
    };
    return (
      <span className={`px-2 py-1 rounded text-xs font-bold ${styles[tier] || styles.NO_DATA}`}>
        {tier}
      </span>
    );
  };

  if (loading) return <div className="p-6">Loading OpenClaw data...</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">🦖 ClawBot Command Center</h1>
        <button
          onClick={handleRefresh}
          className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
        >
          🔄 Force Refresh
        </button>
      </div>

      {/* Regime Banner */}
      <div className={`p-4 rounded-lg ${
        data.regime?.state === 'GREEN' ? 'bg-green-900' :
        data.regime?.state === 'YELLOW' ? 'bg-yellow-900' :
        data.regime?.state === 'RED' ? 'bg-red-900' : 'bg-gray-800'
      }`}>
        <div className="flex justify-between items-center">
          <div>
            <span className="text-2xl font-bold">{data.regime?.state}</span>
            <span className="ml-4">VIX: {data.regime?.vix?.toFixed(1)}</span>
            <span className="ml-4">HMM: {(data.regime?.hmm_confidence * 100)?.toFixed(0)}%</span>
          </div>
          <div className="text-sm text-gray-400">
            Scan: {data.regime?.scan_date}
          </div>
        </div>
        {data.regime?.readme && (
          <p className="mt-2 text-sm">{data.regime.readme}</p>
        )}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Candidates Table - 2 columns */}
        <div className="lg:col-span-2 bg-slate-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">🎯 Scored Candidates</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-slate-700">
                  <th className="text-left p-2">Symbol</th>
                  <th className="text-right p-2">Score</th>
                  <th className="text-center p-2">Tier</th>
                  <th className="text-right p-2">Entry</th>
                  <th className="text-right p-2">Stop</th>
                  <th className="text-center p-2">Whale</th>
                  <th className="text-right p-2">T</th>
                  <th className="text-right p-2">P</th>
                  <th className="text-right p-2">M</th>
                </tr>
              </thead>
              <tbody>
                {data.candidates.map(c => (
                  <tr key={c.symbol} className="border-b border-slate-700 hover:bg-slate-700">
                    <td className="p-2 font-mono font-bold">{c.symbol}</td>
                    <td className="p-2 text-right font-bold">{c.composite_score?.toFixed(1)}</td>
                    <td className="p-2 text-center">{tierBadge(c.tier)}</td>
                    <td className="p-2 text-right">${c.suggested_entry?.toFixed(2) || '-'}</td>
                    <td className="p-2 text-right text-red-400">${c.suggested_stop?.toFixed(2) || '-'}</td>
                    <td className="p-2 text-center">
                      {c.whale_sentiment === 'BULLISH' && '🐂'}
                      {c.whale_sentiment === 'BEARISH' && '🐻'}
                      {!c.whale_sentiment && '-'}
                    </td>
                    <td className="p-2 text-right text-xs">{c.trend_score}</td>
                    <td className="p-2 text-right text-xs">{c.pullback_score}</td>
                    <td className="p-2 text-right text-xs">{c.momentum_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column - Whale Flow + LLM */}
        <div className="space-y-6">
          {/* Whale Flow */}
          <div className="bg-slate-800 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">🐳 Whale Flow Alerts</h2>
            <div className="space-y-2">
              {data.whaleFlow.slice(0, 10).map((w, i) => (
                <div key={i} className="flex justify-between items-center text-sm border-b border-slate-700 pb-2">
                  <span className="font-mono font-bold">{w.ticker}</span>
                  <span className={w.sentiment === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                    {w.sentiment}
                  </span>
                  <span>${(w.premium / 1000000).toFixed(1)}M</span>
                </div>
              ))}
              {data.whaleFlow.length === 0 && (
                <p className="text-gray-500">No whale alerts in latest scan</p>
              )}
            </div>
          </div>

          {/* LLM Summary */}
          <div className="bg-slate-800 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">🤖 AI Analysis</h2>
            {data.llm?.summary_available ? (
              <p className="text-sm text-gray-300">{data.llm.summary}</p>
            ) : (
              <p className="text-gray-500">No LLM analysis available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

#### Task 2.2: Add Route to App.jsx

```jsx
// In App.jsx routes
import ClawBotPanel from './pages/ClawBotPanel';
// ...
<Route path="/clawbot" element={<ClawBotPanel />} />
```

#### Task 2.3: Add to Sidebar.jsx

```jsx
// In Sidebar.jsx navigation items
{ path: '/clawbot', label: '🦖 ClawBot', icon: 'claw' },
```

---

### DAY 3 (Wednesday Feb 26) - Signals.jsx Enhancement
**Time: 4-5 hours**

#### Task 3.1: Add OpenClaw Columns to Signals Table

```jsx
// Update Signals.jsx to fetch OpenClaw scan data
const [openClawScores, setOpenClawScores] = useState({});

useEffect(() => {
  const fetchOpenClawScores = async () => {
    try {
      const res = await api.get('/api/v1/openclaw/scan');
      const candidates = res.data?.top_candidates || [];
      const scoreMap = {};
      candidates.forEach(c => {
        scoreMap[c.symbol] = {
          composite_score: c.composite_score,
          tier: c.tier,
          trend: c.trend_score,
          pullback: c.pullback_score,
          momentum: c.momentum_score
        };
      });
      setOpenClawScores(scoreMap);
    } catch (err) {
      console.error('Failed to fetch OpenClaw scores:', err);
    }
  };
  fetchOpenClawScores();
}, []);

// Add columns to table
<th>Claw Score</th>
<th>Tier</th>
// ...
<td>{openClawScores[signal.symbol]?.composite_score?.toFixed(1) || '-'}</td>
<td>{tierBadge(openClawScores[signal.symbol]?.tier)}</td>
```

---

### DAY 4 (Thursday Feb 27) - Agent Status + Sectors
**Time: 5-6 hours**

#### Task 4.1: AgentSwarmPanel.jsx (for AgentCommandCenter page)

```jsx
// frontend-v2/src/components/agents/AgentSwarmPanel.jsx
// Note: This uses /api/v1/openclaw/health for now
// Full agent heartbeats require new endpoints Espen will add

export default function AgentSwarmPanel() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const fetchHealth = async () => {
      const res = await api.get('/api/v1/openclaw/health');
      setHealth(res.data);
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h2 className="text-lg font-semibold mb-4">📡 Agent Swarm Status</h2>
      <div className="space-y-2">
        <div className="flex justify-between">
          <span>Bridge Connected</span>
          <span className={health?.connected ? 'text-green-400' : 'text-red-400'}>
            {health?.connected ? '✅ Online' : '❌ Offline'}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Gist Configured</span>
          <span>{health?.gist_id_configured ? '✅' : '❌'}</span>
        </div>
        <div className="flex justify-between">
          <span>Candidate Count</span>
          <span>{health?.candidate_count}</span>
        </div>
        <div className="flex justify-between">
          <span>Cache Age</span>
          <span>{health?.cache_age_seconds?.toFixed(0)}s / {health?.cache_ttl_seconds}s</span>
        </div>
        <div className="flex justify-between">
          <span>Last Scan</span>
          <span className="text-xs">{health?.last_scan_timestamp}</span>
        </div>
      </div>
    </div>
  );
}
```

#### Task 4.2: SectorRotationCard.jsx

```jsx
// frontend-v2/src/components/dashboard/SectorRotationCard.jsx
export default function SectorRotationCard() {
  const [sectors, setSectors] = useState([]);

  useEffect(() => {
    const fetchSectors = async () => {
      const res = await api.get('/api/v1/openclaw/sectors');
      setSectors(res.data?.sectors || []);
    };
    fetchSectors();
  }, []);

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h2 className="text-lg font-semibold mb-4">🏛️ Sector Rotation</h2>
      <div className="space-y-2">
        {sectors.map(s => (
          <div key={s.sector} className="flex justify-between items-center">
            <span>{s.sector}</span>
            <span className={s.momentum === 'BULLISH' ? 'text-green-400' : s.momentum === 'BEARISH' ? 'text-red-400' : 'text-gray-400'}>
              {s.score} - {s.momentum}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### DAY 5 (Friday Feb 28) - Testing + Merge
**Time: 3-4 hours**

1. **End-to-end test:** OpenClaw scan → Gist → bridge → Dashboard displays data
2. **Fix any CORS / auth issues**
3. **Clean up open PR, resolve conflicts**
4. **Merge v2 into main branch**

---

## 🔗 API ENDPOINT REFERENCE

| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | `/api/v1/openclaw/scan` | Full scan payload |
| GET | `/api/v1/openclaw/regime` | Market regime + details |
| GET | `/api/v1/openclaw/top?n=10` | Top N candidates |
| GET | `/api/v1/openclaw/health` | Bridge connection status |
| GET | `/api/v1/openclaw/whale-flow` | Whale flow alerts |
| GET | `/api/v1/openclaw/fom` | FOM expected moves |
| GET | `/api/v1/openclaw/llm` | LLM analysis summary |
| GET | `/api/v1/openclaw/sectors` | Sector rankings |
| GET | `/api/v1/openclaw/memory` | Memory IQ, agent rankings, expectancy |
| GET | `/api/v1/openclaw/memory/recall?ticker=AAPL` | 3-stage recall for ticker |
| POST | `/api/v1/openclaw/refresh` | Force cache refresh |

---

## 📊 TIER COLOR CODING

| Tier | Score | Color | Meaning |
|------|-------|-------|--------|
| SLAM | 90+ | 🟡 Gold | Highest conviction |
| HIGH | 80-89 | 🟢 Green | Strong setup |
| TRADEABLE | 70-79 | 🟦 Blue | Valid entry |
| WATCH | 50-69 | ⚪ Gray | Monitor only |
| NO_DATA | <50 | ⚫ Dark | Insufficient data |

---

## 🛠️ ENV SETUP

```bash
# Add to backend/.env
OPENCLAW_GIST_ID=abc123def456...   # GitHub Gist ID
OPENCLAW_GIST_TOKEN=ghp_xxxxx...   # GitHub PAT with gist scope
```

---

## 🚀 WEEK 2 PREVIEW (Mar 2-7)

1. Rename app to "Embodier Trader" across all files
2. Wire RiskIntelligence.jsx to OpenClaw risk data
3. Wire MLInsights.jsx to ensemble_scorer breakdown
4. Wire PerformanceAnalytics.jsx to trade history
5. Add WebSocket real-time signal feed

---

Questions? Slack Espen or email espen@embodier.ai

Last updated: Feb 23, 2026 - Agent Command Center Full Wiring Instructions
