import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { TrendingUp } from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function EquityCurveChart() {
  const { data: apiData, loading, error } = useApi('portfolio', { pollIntervalMs: 60000 });
  const data = apiData?.equityCurve || [];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-secondary/10 border border-secondary/50 rounded-lg p-3 shadow-lg">
          <p className="text-xs text-secondary mb-2">{label}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-success" />
              <span className="text-sm">Portfolio: </span>
              <span className="font-bold text-success">
                ${payload[0]?.value?.toLocaleString()}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-secondary" />
              <span className="text-sm">Benchmark: </span>
              <span className="text-secondary">
                ${payload[1]?.value?.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const initialEquity = data[0]?.equity || 0;
  const currentEquity = data[data.length - 1]?.equity || 0;
  const totalReturn = initialEquity > 0
    ? ((currentEquity - initialEquity) / initialEquity * 100).toFixed(2)
    : '0.00';

  return (
    <div className="bg-secondary/10 border border-secondary/50 rounded-xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-secondary/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-success" />
          <h3 className="font-semibold">Equity Curve</h3>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs text-secondary">30-Day Return</span>
            <p className={`font-bold ${Number(totalReturn) >= 0 ? 'text-success' : 'text-bearish'}`}>
              {Number(totalReturn) >= 0 ? '+' : ''}{totalReturn}%
            </p>
          </div>
          <select className="bg-dark text-sm px-2 py-1 rounded border border-secondary/50">
            <option>30 Days</option>
            <option>90 Days</option>
            <option>1 Year</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      <div className="p-4 h-64">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
              <XAxis 
                dataKey="date" 
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickMargin={8}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                domain={['dataMin - 2000', 'dataMax + 2000']}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ paddingTop: '10px' }}
                formatter={(value) => <span className="text-secondary text-xs">{value}</span>}
              />
              <Line
                type="monotone"
                dataKey="equity"
                name="Portfolio"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#22c55e' }}
              />
              <Line
                type="monotone"
                dataKey="benchmark"
                name="S&P 500"
                stroke="#6b7280"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-secondary text-sm">
            {loading ? 'Loading equity data...' : 'No equity data available'}
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="px-4 py-2 text-xs text-bearish/70 text-center">
          API unavailable — connect backend to see equity curve
        </div>
      )}
    </div>
  );
}
