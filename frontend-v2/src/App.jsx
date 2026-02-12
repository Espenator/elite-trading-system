import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Signals from './pages/Signals';
import Trades from './pages/Trades';
import MLInsights from './pages/MLInsights';
import Patterns from './pages/Patterns';
import Settings from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="signals" element={<Signals />} />
          <Route path="trades" element={<Trades />} />
          <Route path="ml-insights" element={<MLInsights />} />
          <Route path="patterns" element={<Patterns />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
