// frontend-v2/src/components/charts/MonteCarloLC.jsx
import React, { useEffect, useRef } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

/**
 * Monte Carlo Simulation Chart using TradingView's Lightweight Charts.
 * Displays 50+ simulated equity distribution pathways for system survivability analysis.
 * 
 * @param {Array} data - Array of paths, where each path is an array: { time: 'YYYY-MM-DD', value: number }
 */
const MonteCarloLC = ({ data }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRefs = useRef([]); // Store references to all generated line series

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Initialize Chart with Dark Theme / Bloomberg-style config
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#94a3b8', // slate-400
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(51, 65, 85, 0.2)' }, // Faint slate-700
        horzLines: { color: 'rgba(51, 65, 85, 0.2)' },
      },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: {
          width: 1,
          color: 'rgba(148, 163, 184, 0.6)',
          style: 3,
        },
        horzLine: {
          width: 1,
          color: 'rgba(148, 163, 184, 0.6)',
          style: 3,
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.8)',
        autoScale: true,
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.8)',
        timeVisible: true,
        fitContent: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });

    chartRef.current = chart;

    // 2. Handle Resize Observer
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(chartContainerRef.current);

    // Cleanup
    return () => {
      resizeObserver.disconnect();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
      seriesRefs.current = [];
    };
  }, []);

  // 3. Update data when props change
  useEffect(() => {
    if (!chartRef.current) return;

    // Clear existing series if re-rendering
    seriesRefs.current.forEach(series => chartRef.current.removeSeries(series));
    seriesRefs.current = [];

    // Only render real data — no mock/synthetic data
    const chartDataPaths = data && data.length > 0 ? data : [];
    if (chartDataPaths.length === 0) return;

    // Render the simulated pathways (background lines)
    chartDataPaths.forEach((pathData, index) => {
      // Differentiate the "Median/Mean" path from the rest
      const isMedian = index === 0; 
      
      const lineSeries = chartRef.current.addLineSeries({
        color: isMedian ? '#10b981' : 'rgba(56, 189, 248, 0.15)', // Solid emerald for median, faint blue for sims
        lineWidth: isMedian ? 3 : 1,
        crosshairMarkerVisible: isMedian, // Only show marker on the main line to prevent clutter
        priceLineVisible: isMedian,
        lastValueVisible: isMedian,
      });

      lineSeries.setData(pathData);
      seriesRefs.current.push(lineSeries);
    });

    chartRef.current.timeScale().fitContent();
  }, [data]);

  return (
    <div className="w-full h-full relative group">
      {/* Chart Container */}
      <div ref={chartContainerRef} className="absolute inset-0" />
      
      {/* Watermark / HUD Overlay */}
      <div className="absolute top-3 left-4 z-10 pointer-events-none flex flex-col gap-1">
        <h3 className="text-white text-xs font-bold uppercase tracking-wider bg-slate-900/50 px-2 py-1 rounded inline-block">
          Monte Carlo Distribution
        </h3>
        <div className="flex gap-2 px-2">
          <span className="text-emerald-400 text-[10px] font-bold shadow-sm">
            ― Median Pathway
          </span>
          <span className="text-sky-400/70 text-[10px] font-bold shadow-sm">
            ≡ 100 Sims (N)
          </span>
        </div>
      </div>
    </div>
  );
};

export default MonteCarloLC;
