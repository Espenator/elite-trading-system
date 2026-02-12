import LiveSignalFeed from '../components/dashboard/LiveSignalFeed';
import ActivePositions from '../components/dashboard/ActivePositions';
import PerformanceCard from '../components/dashboard/PerformanceCard';
import QuickStats from '../components/dashboard/QuickStats';
import MarketRegimeCard from '../components/dashboard/MarketRegimeCard';
import MLStatusCard from '../components/dashboard/MLStatusCard';
import EquityCurveChart from '../components/charts/EquityCurveChart';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Page title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-400 text-sm">Real-time trading overview</p>
        </div>
      </div>

      {/* Quick stats row */}
      <QuickStats />

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left column - Signals & Positions */}
        <div className="col-span-4 space-y-6">
          <LiveSignalFeed />
          <ActivePositions />
        </div>

        {/* Center column - Charts & Performance */}
        <div className="col-span-5 space-y-6">
          <EquityCurveChart />
          <PerformanceCard />
        </div>

        {/* Right column - ML & Risk */}
        <div className="col-span-3 space-y-6">
          <MarketRegimeCard />
          <MLStatusCard />
        </div>
      </div>
    </div>
  );
}
