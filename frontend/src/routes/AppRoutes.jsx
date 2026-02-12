import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from '../components/layout/MainLayout';
import Dashboard from '../pages/Dashboard';
import TradeExecution from '../pages/TradeExecution';
import PortfolioHeatmap from '../pages/PortfolioHeatmap';
import ModelTraining from '../pages/ModelTraining';
import PerformanceAnalytics from '../pages/PerformanceAnalytics';
import ScreenerResults from '../pages/ScreenerResults';
import Signals from '../pages/Signals';
import Backtest from '../pages/Backtest';
import OrderHistory from '../pages/OrderHistory';
import Settings from '../pages/Settings';
import AccountSettings from '../pages/AccountSettings';
import RiskConfiguration from '../pages/RiskConfiguration';
import StrategySettings from '../pages/StrategySettings';
import Account from '../pages/Account';
import NotFound from '../pages/NotFound';

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="trade" element={<TradeExecution />} />
        <Route path="portfolio" element={<PortfolioHeatmap />} />
        <Route path="model-training" element={<ModelTraining />} />
        <Route path="performance" element={<PerformanceAnalytics />} />
        <Route path="screener" element={<ScreenerResults />} />
        <Route path="signals" element={<Signals />} />
        <Route path="backtest" element={<Backtest />} />
        <Route path="order-history" element={<OrderHistory />} />
        <Route path="settings" element={<Settings />} />
        <Route path="account-settings" element={<AccountSettings />} />
        <Route path="risk-config" element={<RiskConfiguration />} />
        <Route path="strategy" element={<StrategySettings />} />
        <Route path="account" element={<Account />} />
      <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
