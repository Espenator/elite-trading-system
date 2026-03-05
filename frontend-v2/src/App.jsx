// APP ROUTER - Embodier.ai Trading Intelligence System
// Enhanced with React.lazy() for code-splitting & performance
// Architecture doc: V3-ARCHITECTURE.md (14 sidebar pages)
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Layout from "./components/layout/Layout";
import ErrorBoundary from "./components/ErrorBoundary";

// ----------- LAZY PAGE IMPORTS (code-split per route) -----------
// COMMAND section (2 pages)
const Dashboard = lazy(() => import("./pages/Dashboard"));
const AgentCommandCenter = lazy(() => import("./pages/AgentCommandCenter"));

  // INTELLIGENCE section (3 sidebar pages)
const SentimentIntelligence = lazy(() => import("./pages/SentimentIntelligence"));
  const DataSourcesMonitor = lazy(() => import("./pages/DataSourcesMonitor"));
const SignalIntelligenceV3 = lazy(() => import("./pages/SignalIntelligenceV3"));
const SwarmIntelligence = lazy(() => import("./pages/SwarmIntelligence"));

// ML & ANALYSIS section (5 pages)
const MLBrainFlywheel = lazy(() => import("./pages/MLBrainFlywheel"));
const Patterns = lazy(() => import("./pages/Patterns"));
const Backtesting = lazy(() => import("./pages/Backtesting"));
const PerformanceAnalytics = lazy(() => import("./pages/PerformanceAnalytics"));
const MarketRegime = lazy(() => import("./pages/MarketRegime"));

// EXECUTION section (3 pages)
const Trades = lazy(() => import("./pages/Trades"));
const RiskIntelligence = lazy(() => import("./pages/RiskIntelligence"));
const TradeExecution = lazy(() => import("./pages/TradeExecution"));

// SYSTEM section
const Settings = lazy(() => import("./pages/Settings"));

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
            <Route path="dashboard" element={<Suspense fallback={<PageLoader />}><Dashboard /></Suspense>} />
            <Route path="agents" element={<Suspense fallback={<PageLoader />}><AgentCommandCenter /></Suspense>} />
                          <Route path="agents/:tab" element={<Suspense fallback={<PageLoader />}><AgentCommandCenter /></Suspense>} />

            {/* INTELLIGENCE */}
            <Route path="sentiment" element={<Suspense fallback={<PageLoader />}><SentimentIntelligence /></Suspense>} />
                          <Route path="data-sources" element={<Suspense fallback={<PageLoader />}><DataSourcesMonitor /></Suspense>} />
            <Route path="signal-intelligence-v3" element={<Suspense fallback={<PageLoader />}><SignalIntelligenceV3 /></Suspense>} />
            <Route path="swarm-intelligence" element={<Suspense fallback={<PageLoader />}><SwarmIntelligence /></Suspense>} />

            {/* ML & ANALYSIS */}
            <Route path="ml-brain" element={<Suspense fallback={<PageLoader />}><MLBrainFlywheel /></Suspense>} />
            <Route path="patterns" element={<Suspense fallback={<PageLoader />}><Patterns /></Suspense>} />
            <Route path="backtest" element={<Suspense fallback={<PageLoader />}><Backtesting /></Suspense>} />
            <Route path="performance" element={<Suspense fallback={<PageLoader />}><PerformanceAnalytics /></Suspense>} />
            <Route path="market-regime" element={<Suspense fallback={<PageLoader />}><MarketRegime /></Suspense>} />

            {/* EXECUTION */}
            <Route path="trades" element={<Suspense fallback={<PageLoader />}><Trades /></Suspense>} />
            <Route path="risk" element={<Suspense fallback={<PageLoader />}><RiskIntelligence /></Suspense>} />
            <Route path="trade-execution" element={<Suspense fallback={<PageLoader />}><TradeExecution /></Suspense>} />

            {/* SYSTEM */}
            <Route path="settings" element={<Suspense fallback={<PageLoader />}><Settings /></Suspense>} />
          </Route>
        </Routes>
        <ToastContainer position="bottom-right" theme="dark" />
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
