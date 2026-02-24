// APP ROUTER - Embodier.ai Trading Intelligence System
// OLEH: This is the main router. Every page listed in the sidebar has a route here.
// If you add a new page, add: 1) import, 2) route, 3) sidebar entry in Sidebar.jsx
// All 16 pages map 1:1 to backend modules per V2-EMBODIER-AI-README.md

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Layout from "./components/layout/Layout";
import ErrorBoundary from "./components/ErrorBoundary";

// ----------- PAGE IMPORTS -----------
// COMMAND section (4 pages)
import Dashboard from "./pages/Dashboard";
import AgentCommandCenter from "./pages/AgentCommandCenter";
import OperatorConsole from "./pages/OperatorConsole";
import ClawBotPanel from "./pages/ClawBotPanel";

// INTELLIGENCE section (5 pages)
import Signals from "./pages/Signals";
  import SignalHeatmap from "./pages/SignalHeatmap";
import SentimentIntelligence from "./pages/SentimentIntelligence";
import DataSourcesMonitor from "./pages/DataSourcesMonitor";
import YouTubeKnowledge from "./pages/YouTubeKnowledge";

// ML & ANALYSIS section (4 pages)
import MLInsights from "./pages/MLInsights";
import Patterns from "./pages/Patterns";
import Backtesting from "./pages/Backtesting";
import PerformanceAnalytics from "./pages/PerformanceAnalytics";

// EXECUTION section (3 pages)
import Trades from "./pages/Trades";
import RiskIntelligence from "./pages/RiskIntelligence";
import StrategyIntelligence from "./pages/StrategyIntelligence";

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
            <Route path="operator" element={<OperatorConsole />} />
            <Route path="clawbot" element={<ClawBotPanel />} />

            {/* INTELLIGENCE */}
            <Route path="signals" element={<Signals />} />
            <Route path="signal-heatmap" element={<SignalHeatmap />} />
            <Route path="sentiment" element={<SentimentIntelligence />} />
            <Route path="data-sources" element={<DataSourcesMonitor />} />
            <Route path="youtube" element={<YouTubeKnowledge />} />

            {/* ML & ANALYSIS */}
            <Route path="ml-insights" element={<MLInsights />} />
            <Route path="patterns" element={<Patterns />} />
            <Route path="backtest" element={<Backtesting />} />
            <Route path="performance" element={<PerformanceAnalytics />} />

            {/* EXECUTION */}
            <Route path="trades" element={<Trades />} />
            <Route path="risk" element={<RiskIntelligence />} />
            <Route path="strategy" element={<StrategyIntelligence />} />

            {/* SYSTEM */}
            <Route path="settings" element={<Settings />} />

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
