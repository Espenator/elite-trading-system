// APP ROUTER - Embodier.ai Glass House Intelligence System
// OLEH: This is the main router. Every page listed in the sidebar has a route here.
// If you add a new page, add: 1) import, 2) route, 3) sidebar entry in Sidebar.jsx
// All 15 pages map 1:1 to backend modules per V2-EMBODIER-AI-README.md

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import Layout from './components/layout/Layout';

// ----------- PAGE IMPORTS -----------
// COMMAND section
import Dashboard from './pages/Dashboard';
import AgentCommandCenter from './pages/AgentCommandCenter';

// INTELLIGENCE section
import Signals from './pages/Signals';

// ML & ANALYSIS section
import MLInsights from './pages/MLInsights';
import Patterns from './pages/Patterns';
import Backtesting from './pages/Backtesting';
import PerformanceAnalytics from './pages/PerformanceAnalytics';

// PORTFOLIO section
import Portfolio from './pages/Portfolio';

// EXECUTION section
import Trades from './pages/Trades';

// SYSTEM section
import Settings from './pages/Settings';

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
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* Default redirect */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* COMMAND */}
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="agents" element={<AgentCommandCenter />} />

          {/* INTELLIGENCE */}
          <Route path="signals" element={<Signals />} />

          {/* ML & ANALYSIS */}
          <Route path="ml-insights" element={<MLInsights />} />
          <Route path="patterns" element={<Patterns />} />
          <Route path="backtest" element={<Backtesting />} />
          <Route path="performance" element={<PerformanceAnalytics />} />

          {/* PORTFOLIO */}
          <Route path="portfolio" element={<Portfolio />} />

          {/* EXECUTION */}
          <Route path="trades" element={<Trades />} />

          {/* SYSTEM */}
          <Route path="settings" element={<Settings />} />

          {/* 404 catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
