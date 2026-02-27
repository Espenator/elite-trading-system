// frontend-v2/src/components/charts/PatternFrequencyLC.jsx
import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

/**
 * Pattern Frequency Histogram Chart using TradingView Lightweight Charts.
 * Replaces Recharts BarChart on the Patterns page sector frequency view.
 *
 * @param {Array} data - Array of { name: string, patterns: number, color: string }
 * @param {number} height - Chart height in pixels (default 300)
 */
const PatternFrequencyLC = ({ data = [], height = 300 }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      height,
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#94a3b8',
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(51, 65, 85, 0.4)' },
        horzLines: { color: 'rgba(51, 65, 85, 0.4)' },
      },
      crosshair: {
        vertLine: { width: 1, color: 'rgba(148, 163, 184, 0.4)', style: 3 },
        horzLine: { width: 1, color: 'rgba(148, 163, 184, 0.4)', style: 3 },
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.8)',
        autoScale: true,
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.8)',
        fitContent: true,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
    });

    const series = chart.addHistogramSeries({
      color: '#6366f1',
      priceFormat: { type: 'volume' },
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !data.length) return;

    // Convert sector data to histogram format using index as time
    const histData = data.map((d, i) => ({
      time: i,
      value: d.patterns || d.count || 0,
      color: d.color || '#6366f1',
    }));

    seriesRef.current.setData(histData);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return (
    <div className="relative">
      <div ref={chartContainerRef} className="w-full" style={{ height }} />
      {/* Sector labels overlay */}
      {data.length > 0 && (
        <div className="flex justify-between px-2 mt-1">
          {data.map((d, i) => (
            <span key={i} className="text-[9px] text-slate-500 truncate" style={{ maxWidth: `${100 / data.length}%` }}>
              {d.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default PatternFrequencyLC;
