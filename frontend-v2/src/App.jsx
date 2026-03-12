// APP ROUTER - Embodier.ai Trading Intelligence System
// Enhanced with React.lazy() for code-splitting & performance
// Architecture doc: V3-ARCHITECTURE.md (14 sidebar pages)
import { lazy, Suspense, Component } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Layout from "./components/layout/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import PageSkeleton from "./components/ui/PageSkeleton";
// CNSProvider is provided by Layout — no need to import here

// Per-page error boundary that preserves navigation chrome
class PageBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return <PageErrorFallback error={this.state.error} onReset={() => this.setState({ hasError: false, error: null })} />;
    }
    return this.props.children;
  }
}

/** Wraps a lazy component with Suspense + page-level error boundary */
function P({ children }) {
  return <PageBoundary><Suspense fallback={<PageLoader />}>{children}</Suspense></PageBoundary>;
}

// ----------- LAZY PAGE IMPORTS (code-split per route) -----------
// COMMAND section (2 pages)
const Dashboard = lazy(() => import("./pages/Dashboard"));
const AgentCommandCenter = lazy(() => import("./pages/AgentCommandCenter"));

  // INTELLIGENCE section (3 sidebar pages)
const SentimentIntelligence = lazy(() => import("./pages/SentimentIntelligence"));
  const DataSourcesMonitor = lazy(() => import("./pages/DataSourcesMonitor"));
const SignalIntelligenceV3 = lazy(() => import("./pages/SignalIntelligenceV3"));
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

// ----------- LOADING FALLBACK (shimmer skeleton) -----------
function PageLoader() {
  return (
    <div className="flex flex-col h-full p-6">
      <PageSkeleton lines={12} className="max-w-2xl" />
    </div>
  );
}

// ----------- 404 NOT FOUND -----------
function NotFound() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-cyan-400 mb-2">404</h1>
        <p className="text-sm text-gray-400 mb-4">Page not found</p>
        <a href="/dashboard" className="text-xs text-cyan-400 hover:text-cyan-300 underline">
          Back to Dashboard
        </a>
      </div>
    </div>
  );
}

// ----------- PAGE ERROR BOUNDARY (preserves sidebar) -----------
function PageErrorFallback({ error, onReset }) {
  return (
    <div className="flex items-center justify-center h-full p-6">
      <div className="max-w-md text-center">
        <h2 className="text-lg font-bold text-red-400 mb-2">Page Error</h2>
        <p className="text-sm text-gray-400 mb-4">{error?.message || "This page crashed unexpectedly."}</p>
        <div className="flex gap-3 justify-center">
          <button
            type="button"
            onClick={onReset}
            className="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 text-sm"
          >
            Try again
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 rounded-lg bg-secondary/20 text-white border border-secondary/40 hover:bg-secondary/30 text-sm"
          >
            Go to Dashboard
          </a>
        </div>
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
            {/* COMMAND — Dashboard is inside Layout so it gets the correct sidebar */}
            <Route path="dashboard" element={<P><Dashboard /></P>} />
            <Route path="agents" element={<P><AgentCommandCenter /></P>} />
            <Route path="agents/:tab" element={<P><AgentCommandCenter /></P>} />

            {/* INTELLIGENCE */}
            <Route path="sentiment" element={<P><SentimentIntelligence /></P>} />
            <Route path="data-sources" element={<P><DataSourcesMonitor /></P>} />
            <Route path="signal-intelligence-v3" element={<P><SignalIntelligenceV3 /></P>} />

            {/* ML & ANALYSIS */}
            <Route path="ml-brain" element={<P><MLBrainFlywheel /></P>} />
            <Route path="patterns" element={<P><Patterns /></P>} />
            <Route path="backtest" element={<P><Backtesting /></P>} />
            <Route path="performance" element={<P><PerformanceAnalytics /></P>} />
            <Route path="market-regime" element={<P><MarketRegime /></P>} />

            {/* EXECUTION */}
            <Route path="trades" element={<P><Trades /></P>} />
            <Route path="risk" element={<P><RiskIntelligence /></P>} />
            <Route path="trade-execution" element={<P><TradeExecution /></P>} />

            {/* SYSTEM */}
            <Route path="settings" element={<P><Settings /></P>} />

            {/* 404 Catch-all */}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
        <ToastContainer position="bottom-right" theme="dark" />
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
