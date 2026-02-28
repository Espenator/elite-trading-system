import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import { TrendingUp } from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function EquityCurveChart() {
  const { data: apiData, loading, error } = useApi('portfolio', { pollIntervalMs: 60000 });
  const data = apiData?.equityCurve || [];
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // Dispose previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 240,
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#6b7280',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#2d3748', style: 1 },
        horzLines: { color: '#2d3748', style: 1 },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
      },
      crosshair: {
        vertLine: { color: '#6b7280', width: 1, style: 2 },
        horzLine: { color: '#6b7280', width: 1, style: 2 },
      },
    });

    chartRef.current = chart;

    // Portfolio line
    const portfolioSeries = chart.addLineSeries({
      color: '#22c55e',
      lineWidth: 2,
      crosshairMarkerRadius: 4,
      title: 'Portfolio',
    });

    // Benchmark line (dashed via overlay)
    const benchmarkSeries = chart.addLineSeries({
      color: '#6b7280',
      lineWidth: 1,
      lineStyle: 2, // dashed
      title: 'S&P 500',
    });

    // Map data to LW Charts format { time, value }
    const portfolioData = data
      .filter(d => d.date && d.equity != null)
      .map(d => ({ time: d.date, value: d.equity }));

    const benchmarkData = data
      .filter(d => d.date && d.benchmark != null)
      .map(d => ({ time: d.date, value: d.benchmark }));

    if (portfolioData.length) portfolioSeries.setData(portfolioData);
    if (benchmarkData.length) benchmarkSeries.setData(benchmarkData);

    chart.timeScale().fitContent();

    // Resize observer
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    ro.observe(chartContainerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

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
      <div className="p-4">
        {data.length > 0 ? (
          <div ref={chartContainerRef} />
        ) : (
          <div className="flex items-center justify-center h-64 text-secondary text-sm">
            {loading ? 'Loading equity data...' : 'No equity data available'}
          </div>
        )}
      </div>
      {/* Error state */}
      {error && (
        <div className="px-4 py-2 text-xs text-bearish/70 text-center">
          API unavailable - connect backend to see equity curve
        </div>
      )}
    </div>
  );
}
