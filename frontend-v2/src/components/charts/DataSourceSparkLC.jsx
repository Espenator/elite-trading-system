// frontend-v2/src/components/charts/DataSourceSparkLC.jsx
import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

/**
 * Compact sparkline chart for Data Sources Monitor page.
 * Replaces Recharts LineChart sparklines and AreaChart throughput chart.
 * Uses LW Charts for consistent Bloomberg-style rendering.
 *
 * @param {Array} data - Array of { time: number, value: number } or { time: number, latency: number }
 * @param {string} color - Line color (default cyan)
 * @param {string} type - 'line' | 'area' | 'histogram' (default 'area')
 * @param {number} height - Chart height in pixels (default 60)
 * @param {boolean} showAxis - Show price/time axis (default false for sparklines)
 */
const DataSourceSparkLC = ({ data = [], color = '#06b6d4', type = 'area', height = 60, showAxis = false }) => {
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
        fontSize: 9,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      crosshair: {
        vertLine: { visible: false },
        horzLine: { visible: false },
      },
      rightPriceScale: {
        visible: showAxis,
        borderVisible: false,
      },
      leftPriceScale: { visible: false },
      timeScale: {
        visible: showAxis,
        borderVisible: false,
        fitContent: true,
      },
      handleScroll: false,
      handleScale: false,
    });

    let series;
    if (type === 'histogram') {
      series = chart.addHistogramSeries({
        color,
        priceScaleId: 'right',
        priceFormat: { type: 'volume' },
      });
    } else if (type === 'line') {
      series = chart.addLineSeries({
        color,
        lineWidth: 1,
        priceScaleId: 'right',
        crosshairMarkerVisible: false,
      });
    } else {
      series = chart.addAreaSeries({
        lineColor: color,
        topColor: color.replace(')', ', 0.3)').replace('rgb', 'rgba'),
        bottomColor: 'transparent',
        lineWidth: 1,
        priceScaleId: 'right',
        crosshairMarkerVisible: false,
      });
    }

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
  }, [type, color]);

  useEffect(() => {
    if (!seriesRef.current || !data.length) return;

    // Normalize data: accept { time, value } or { time, latency } or { time, val }
    const today = new Date().toISOString().split('T')[0];
    const normalized = data.map((d, i) => ({
      time: i, // Use index as time for sparklines (business day format not needed)
      value: d.value ?? d.latency ?? d.val ?? 0,
    }));

    seriesRef.current.setData(normalized);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={chartContainerRef} className="w-full" style={{ height }} />;
};

export default DataSourceSparkLC;
