// TRADES PAGE - Embodier.ai Glass House Intelligence System
// Trade management: active positions, order history, P&L tracking
import { useState } from 'react';
import { TrendingUp, Clock, DollarSign, ArrowUpRight } from 'lucide-react';
import Card from '../components/ui/Card';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

const ACTIVE_POSITIONS = [
  { id: 1, ticker: 'AAPL', side: 'Long', qty: 50, entry: 189.50, current: 192.30, pnl: 140, pnlPct: 1.48, stop: 185.00, target: 198.00, signal: 'AI Signal #1', time: '2h ago' },
  { id: 2, ticker: 'TSLA', side: 'Long', qty: 30, entry: 245.30, current: 248.10, pnl: 84, pnlPct: 1.14, stop: 240.00, target: 260.00, signal: 'AI Signal #2', time: '4h ago' },
  { id: 3, ticker: 'NVDA', side: 'Long', qty: 10, entry: 875.00, current: 868.20, pnl: -68, pnlPct: -0.78, stop: 850.00, target: 920.00, signal: 'AI Signal #3', time: '1d ago' },
  { id: 4, ticker: 'SPY', side: 'Short', qty: 100, entry: 502.10, current: 500.85, pnl: 125, pnlPct: 0.25, stop: 506.00, target: 495.00, signal: 'AI Signal #4', time: '3h ago' },
];

const TRADE_HISTORY = [
  { id: 101, ticker: 'MSFT', side: 'Long', qty: 40, entry: 408.20, exit: 418.50, pnl: 412, pnlPct: 2.52, duration: '2d 4h', date: 'Feb 14' },
  { id: 102, ticker: 'AMD', side: 'Long', qty: 60, entry: 165.00, exit: 172.30, pnl: 438, pnlPct: 4.42, duration: '1d 8h', date: 'Feb 13' },
  { id: 103, ticker: 'META', side: 'Short', qty: 20, entry: 590.00, exit: 582.40, pnl: 152, pnlPct: 1.29, duration: '6h', date: 'Feb 13' },
  { id: 104, ticker: 'GOOGL', side: 'Long', qty: 50, entry: 178.50, exit: 175.20, pnl: -165, pnlPct: -1.85, duration: '1d 2h', date: 'Feb 12' },
  { id: 105, ticker: 'AMZN', side: 'Long', qty: 25, entry: 185.00, exit: 192.80, pnl: 195, pnlPct: 4.22, duration: '3d', date: 'Feb 11' },
];

export default function Trades() {
  const [tab, setTab] = useState('active');

  const totalPnl = ACTIVE_POSITIONS.reduce((sum, p) => sum + p.pnl, 0);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Trades</h1>
          <p className="text-sm text-secondary mt-1">Manage positions and review history</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant={totalPnl >= 0 ? 'success' : 'danger'} size="lg" className="px-4 py-2">
            Today: {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(0)}
          </Badge>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Positions', value: ACTIVE_POSITIONS.length, icon: TrendingUp, color: 'text-primary' },
          { label: 'Unrealized P&L', value: `$${totalPnl >= 0 ? '+' : ''}${totalPnl}`, icon: DollarSign, color: totalPnl >= 0 ? 'text-success' : 'text-danger' },
          { label: 'Win Rate (30d)', value: '68.5%', icon: ArrowUpRight, color: 'text-success' },
          { label: 'Avg Hold Time', value: '1.4 days', icon: Clock, color: 'text-warning' },
        ].map((stat, i) => (
          <Card key={i} noPadding className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              <span className="text-xs text-secondary">{stat.label}</span>
            </div>
            <div className="text-xl font-bold text-white">{stat.value}</div>
          </Card>
        ))}
      </div>

      <div className="flex gap-2 border-b border-secondary/50 pb-0">
        {['active', 'history'].map(t => (
          <Button
            key={t}
            variant={tab === t ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setTab(t)}
            className={tab === t ? 'border-b-2 border-primary rounded-b-none' : 'rounded-b-none'}
          >
            {t === 'active' ? `Active (${ACTIVE_POSITIONS.length})` : `History (${TRADE_HISTORY.length})`}
          </Button>
        ))}
      </div>

      {tab === 'active' && (
        <Card noPadding className="overflow-hidden">
          <DataTable
            columns={[
              { key: 'ticker', label: 'Ticker', render: (v) => <span className="font-semibold text-white">{v}</span> },
              { key: 'side', label: 'Side', render: (v) => <Badge variant={v === 'Long' ? 'success' : 'danger'}>{v}</Badge> },
              { key: 'qty', label: 'Qty', cellClassName: 'text-right' },
              { key: 'entry', label: 'Entry', cellClassName: 'text-right', render: (v) => `$${Number(v).toFixed(2)}` },
              { key: 'current', label: 'Current', cellClassName: 'text-right', render: (v) => `$${Number(v).toFixed(2)}` },
              { key: 'pnl', label: 'P&L', cellClassName: 'text-right', render: (_, row) => (
                <span className={row.pnl >= 0 ? 'text-success' : 'text-danger'}>
                  {row.pnl >= 0 ? '+' : ''}${row.pnl} ({row.pnlPct >= 0 ? '+' : ''}{row.pnlPct}%)
                </span>
              ) },
              { key: 'stop', label: 'Stop', cellClassName: 'text-right text-danger', render: (v) => `$${Number(v).toFixed(2)}` },
              { key: 'target', label: 'Target', cellClassName: 'text-right text-success', render: (v) => `$${Number(v).toFixed(2)}` },
              { key: 'signal', label: 'Signal', render: (v) => <span className="text-secondary">{v}</span> },
              { key: 'id', label: 'Actions', cellClassName: 'text-right', render: () => <Button variant="danger" size="sm">Close</Button> },
            ]}
            data={ACTIVE_POSITIONS}
          />
        </Card>
      )}

      {tab === 'history' && (
        <Card noPadding className="overflow-hidden">
          <DataTable
            columns={[
              { key: 'date', label: 'Date', render: (v) => <span className="text-secondary">{v}</span> },
              { key: 'ticker', label: 'Ticker', render: (v) => <span className="font-semibold text-white">{v}</span> },
              { key: 'side', label: 'Side', render: (v) => <Badge variant={v === 'Long' ? 'success' : 'danger'}>{v}</Badge> },
              { key: 'qty', label: 'Qty', cellClassName: 'text-right' },
              { key: 'entry', label: 'Entry', cellClassName: 'text-right', render: (v) => `$${Number(v).toFixed(2)}` },
              { key: 'exit', label: 'Exit', cellClassName: 'text-right', render: (v) => `$${Number(v).toFixed(2)}` },
              { key: 'pnl', label: 'P&L', cellClassName: 'text-right', render: (_, row) => (
                <span className={row.pnl >= 0 ? 'text-success' : 'text-danger'}>
                  {row.pnl >= 0 ? '+' : ''}${row.pnl} ({row.pnlPct >= 0 ? '+' : ''}{row.pnlPct}%)
                </span>
              ) },
              { key: 'duration', label: 'Duration', cellClassName: 'text-right', render: (v) => <span className="text-secondary">{v}</span> },
            ]}
            data={TRADE_HISTORY}
          />
        </Card>
      )}
    </div>
  );
}
