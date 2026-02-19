import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Activity,
  DollarSign,
  Percent
} from 'lucide-react';
import { mockPerformance, mockPositions } from '../../data/mockData';
import clsx from 'clsx';

export default function QuickStats() {
  const perf = mockPerformance;
  const openPnl = mockPositions.reduce((sum, p) => sum + p.pnlDollars, 0);

  const stats = [
    {
      label: "Today's P&L",
      value: `$${perf.todayPnl.toLocaleString()}`,
      change: perf.todayPnl >= 0 ? '+2.1%' : '-2.1%',
      isPositive: perf.todayPnl >= 0,
      icon: DollarSign,
    },
    {
      label: 'Open P&L',
      value: `$${openPnl.toLocaleString()}`,
      change: `${mockPositions.length} positions`,
      isPositive: openPnl >= 0,
      icon: Activity,
    },
    {
      label: 'Win Rate',
      value: `${perf.winRate.toFixed(1)}%`,
      change: `${perf.winners}W / ${perf.losers}L`,
      isPositive: perf.winRate >= 60,
      icon: Target,
    },
    {
      label: 'Avg R-Multiple',
      value: `${perf.avgRMultiple.toFixed(2)}R`,
      change: `${perf.totalTrades} trades`,
      isPositive: perf.avgRMultiple >= 1,
      icon: Percent,
    },
    {
      label: 'Week P&L',
      value: `$${perf.weekPnl.toLocaleString()}`,
      change: '+4.2%',
      isPositive: perf.weekPnl >= 0,
      icon: TrendingUp,
    },
    {
      label: 'Max Drawdown',
      value: `${perf.maxDrawdown.toFixed(1)}%`,
      change: 'From peak',
      isPositive: perf.maxDrawdown < 5,
      icon: TrendingDown,
    },
  ];

  return (
    <div className="grid grid-cols-6 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-secondary/10 border border-secondary/50 rounded-xl p-4 card-hover"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-secondary">{stat.label}</span>
            <stat.icon className={clsx(
              'w-4 h-4',
              stat.isPositive ? 'text-bullish' : 'text-bearish'
            )} />
          </div>
          <div className={clsx(
            'text-xl font-bold',
            stat.isPositive ? 'text-bullish' : 'text-bearish'
          )}>
            {stat.value}
          </div>
          <div className="text-xs text-secondary mt-1">
            {stat.change}
          </div>
        </div>
      ))}
    </div>
  );
}
