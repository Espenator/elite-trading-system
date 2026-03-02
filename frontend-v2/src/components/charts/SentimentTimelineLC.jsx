// frontend-v2/src/components/charts/SentimentTimelineLC.jsx
import React, { useEffect, useRef } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

/**
 * Sentiment Timeline Chart using TradingView Lightweight Charts.
 * Replaces Recharts ComposedChart (AreaChart + BarChart) on SentimentIntelligence page.
 *
 * @param {Array} data - Array of { time: 'HH:00', sentiment: number (-1 to 1), volume: number }
 * @param {number} height - Chart height in pixels (default 280)
 */
const SentimentTimelineLC = ({ data = [], height = 280 }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const sentimentSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);

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
        mode: CrosshairMode.Magnet,
        vertLine: { width: 1, color: 'rgba(148, 163, 184, 0.4)', style: 3 },
        horzLine: { width: 1, color: 'rgba(148, 163, 184, 0.4)', style: 3 },
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.8)',
        autoScale: true,
      },
      leftPriceScale: {
        visible: true,
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

    // Sentiment area series (right scale)
    const sentimentSeries = chart.addAreaSeries({
      lineColor: '#06b6d4',
      topColor: 'rgba(6, 182, 212, 0.4)',
      bottomColor: 'rgba(6, 182, 212, 0.0)',
      lineWidth: 2,
      priceScaleId: 'right',
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    });

    // Volume histogram series (left scale)
    const volumeSeries = chart.addHistogramSeries({
      color: 'rgba(99, 102, 241, 0.5)',
      priceScaleId: 'left',
      priceFormat: { type: 'volume' },
    });

    chartRef.current = chart;
    sentimentSeriesRef.current = sentimentSeries;
    volumeSeriesRef.current = volumeSeries;

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

  // Update data when props change
  useEffect(() => {
    if (!sentimentSeriesRef.current || !volumeSeriesRef.current || !data.length) return;

    // Convert hourly string keys to sequential time values for LW Charts
    const today = new Date().toISOString().split('T')[0];
    const sentimentData = data.map((d, i) => ({
      time: `${today}T${String(d.time).padStart(5, '0')}:00`,
      value: d.sentiment,
    })).sort((a, b) => a.time.localeCompare(b.time));

    const volumeData = data.map((d, i) => ({
      time: `${today}T${String(d.time).padStart(5, '0')}:00`,
      value: d.volume,
      color: d.sentiment >= 0 ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
    })).sort((a, b) => a.time.localeCompare(b.time));

    sentimentSeriesRef.current.setData(sentimentData);
    volumeSeriesRef.current.setData(volumeData);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={chartContainerRef} className="w-full" style={{ height }} />;
};

export default SentimentTimelineLC;
