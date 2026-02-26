// frontend-v2/src/components/charts/RiskEquityLC.jsx
import React, { useEffect, useRef } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

/**
 * High-performance Equity Curve Chart using TradingView's Lightweight Charts.
 * Designed for the Risk Intelligence dashboard.
 * 
 * @param {Array} data - Array of objects: { time: 'YYYY-MM-DD', value: number }
 */
const RiskEquityLC = ({ data }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

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
        vertLines: { color: 'rgba(51, 65, 85, 0.4)' }, // slate-700/40
        horzLines: { color: 'rgba(51, 65, 85, 0.4)' },
      },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: {
          width: 1,
          color: 'rgba(148, 163, 184, 0.4)',
          style: 3, // Dashed
        },
        horzLine: {
          width: 1,
          color: 'rgba(148, 163, 184, 0.4)',
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

    // 2. Create the Area Series for the Equity Curve
    const areaSeries = chart.addAreaSeries({
      lineColor: '#06b6d4', // cyan-500
      topColor: 'rgba(6, 182, 212, 0.4)',
      bottomColor: 'rgba(6, 182, 212, 0.0)',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    });

    chartRef.current = chart;
    seriesRef.current = areaSeries;

    // 3. Handle Resize Observer
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
    };
  }, []);

  // 4. Update data when props change
  useEffect(() => {
    if (!seriesRef.current || !data) return;
    
    // Default fallback mock data if none provided (for UI testing)
    const chartData = data.length > 0 ? data : generateMockEquityData();
    
    seriesRef.current.setData(chartData);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return (
    <div className="w-full h-full relative group">
      {/* Chart Container */}
      <div ref={chartContainerRef} className="absolute inset-0" />
      
      {/* Watermark / Legend Overlay */}
      <div className="absolute top-3 left-4 z-10 pointer-events-none">
        <h3 className="text-white text-xs font-bold uppercase tracking-wider bg-slate-900/50 px-2 py-1 rounded">
          System Equity Curve
        </h3>
        <p className="text-cyan-400 text-[10px] mt-1 px-2 font-bold shadow-sm">
          ALGO: VELEZ V2.0 + UCS-REGIME
        </p>
      </div>
    </div>
  );
};

// Helper function to generate realistic looking equity curve for the UI
function generateMockEquityData() {
  const data = [];
  let currentValue = 1000000; // $1M starting capital
  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 6);

  for (let i = 0; i < 180; i++) {
    const time = new Date(startDate);
    time.setDate(time.getDate() + i);
    
    // Add realistic drift and volatility
    const drift = 500;
    const vol = (Math.random() - 0.48) * 15000; 
    currentValue += drift + vol;

    data.push({
      time: time.toISOString().split('T')[0],
      value: currentValue
    });
  }
  return data;
}

export default RiskEquityLC;
