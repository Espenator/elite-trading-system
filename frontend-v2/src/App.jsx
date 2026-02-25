// APP ROUTER - Embodier.ai Trading Intelligence System
// OLEH: This is the main router. Every page listed in the sidebar has a route here.
// If you add a new page, add: 1) import, 2) route, 3) sidebar entry in Sidebar.jsx
// All 15 pages map 1:1 to backend modules per V2-EMBODIER-AI-README.md
// V3 CONSOLIDATION: Reduced from 18 to 14 pages, then added ML Brain & Flywheel (15 total)

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Layout from "./components/layout/Layout";
import ErrorBoundary from "./components/ErrorBoundary";

// ----------- PAGE IMPORTS -----------
// COMMAND section (2 pages)
import Dashboard from "./pages/Dashboard";
import AgentCommandCenter from "./pages/AgentCommandCenter";

// INTELLIGENCE section (3 pages)
import Signals from "./pages/Signals";
import SentimentIntelligence from "./pages/SentimentIntelligence";
import DataSourcesMonitor from "./pages/DataSourcesMonitor";

// ML & ANALYSIS section (6 pages)
import MLInsights from "./pages/MLInsights";
import MLBrainFlywheel from "./pages/MLBrainFlywheel";
import Patterns from "./pages/Patterns";
import Backtesting from "./pages/Backtesting";
import PerformanceAnalytics from "./pages/PerformanceAnalytics";
import MarketRegime from "./pages/MarketRegime";

// EXECUTION section (3 pages)
import Trades from "./pages/Trades";
import RiskIntelligence from "./pages/RiskIntelligence";
import TradeExecution from "./pages/TradeExecution";

// SYSTEM section
import Settings from "./pages/Settings";

// ----------- LOADING FALLBACK -----------
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-gray-400">Loading module...</span>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Layout />}>
            {/* Default redirect */}
            <Route index element={<Navigate to="/dashboard" replace />} />

            {/* COMMAND */}
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="agents" element={<AgentCommandCenter />} />

            {/* INTELLIGENCE */}
            <Route path="signals" element={<Signals />} />
            <Route path="sentiment" element={<SentimentIntelligence />} />
            <Route path="data-sources" element={<DataSourcesMonitor />} />

            {/* ML & ANALYSIS */}
            <Route path="ml-insights" element={<MLInsights />} />
            <Route path="ml-brain" element={<MLBrainFlywheel />} />
            <Route path="patterns" element={<Patterns />} />
            <Route path="backtest" element={<Backtesting />} />
            <Route path="performance" element={<PerformanceAnalytics />} />
            <Route path="market-regime" element={<MarketRegime />} />

            {/* EXECUTION */}
            <Route path="trades" element={<Trades />} />
            <Route path="risk" element={<RiskIntelligence />} />
            <Route path="trade-execution" element={<TradeExecution />} />

            {/* SYSTEM */}
            <Route path="settings" element={<Settings />} />

            {/* Legacy redirects for bookmarks */}
            <Route path="operator" element={<Navigate to="/agents" replace />} />
            <Route path="signal-heatmap" element={<Navigate to="/signals" replace />} />
            <Route path="youtube" element={<Navigate to="/sentiment" replace />} />
            <Route path="strategy" element={<Navigate to="/backtest" replace />} />

            {/* 404 catch-all */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </ErrorBoundary>
      <ToastContainer position="top-right" theme="dark" autoClose={4000} />
    </BrowserRouter>
  );
}

export default App;
