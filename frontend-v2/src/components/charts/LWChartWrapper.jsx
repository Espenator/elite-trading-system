import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

/**
 * Generic Lightweight Charts wrapper — Aurora design system.
 *
 * Props:
 *   data      — array of { time, value } (line) or { time, open, high, low, close } (candlestick)
 *   type      — 'line' | 'area' | 'candlestick' | 'histogram' | 'bar'  (default: 'line')
 *   height    — CSS height string (default: '100%')
 *   options   — extra chart options merged into defaults
 *   seriesOpts — extra series options (color, lineWidth, etc.)
 *   className — extra CSS classes
 */
export default function LWChartWrapper({
  data = [],
  type = 'line',
  height = '100%',
  options = {},
  seriesOpts = {},
  className = '',
}) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#9CA3AF',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(42,52,68,0.3)' },
        horzLines: { color: 'rgba(42,52,68,0.3)' },
      },
      timeScale: {
        borderColor: 'rgba(42,52,68,0.5)',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: 'rgba(42,52,68,0.5)',
      },
      crosshair: {
        vertLine: { color: 'rgba(0,217,255,0.3)', labelBackgroundColor: '#111827' },
        horzLine: { color: 'rgba(0,217,255,0.3)', labelBackgroundColor: '#111827' },
      },
      handleScroll: { vertTouchDrag: false },
      ...options,
    });
    chartRef.current = chart;

    let series;
    const baseOpts = { ...seriesOpts };

    switch (type) {
      case 'area':
        series = chart.addAreaSeries({
          lineColor: '#00D9FF',
          topColor: 'rgba(0,217,255,0.3)',
          bottomColor: 'rgba(0,217,255,0.02)',
          lineWidth: 2,
          ...baseOpts,
        });
        break;
      case 'candlestick':
        series = chart.addCandlestickSeries({
          upColor: '#10B981',
          downColor: '#EF4444',
          borderUpColor: '#10B981',
          borderDownColor: '#EF4444',
          wickUpColor: '#10B981',
          wickDownColor: '#EF4444',
          ...baseOpts,
        });
        break;
      case 'histogram':
        series = chart.addHistogramSeries({
          color: '#00D9FF',
          ...baseOpts,
        });
        break;
      case 'bar':
        series = chart.addBarSeries({
          upColor: '#10B981',
          downColor: '#EF4444',
          ...baseOpts,
        });
        break;
      default: // line
        series = chart.addLineSeries({
          color: '#00D9FF',
          lineWidth: 2,
          ...baseOpts,
        });
    }

    seriesRef.current = series;
    if (data.length) series.setData(data);
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [type]); // recreate on type change

  // Update data without recreating chart
  useEffect(() => {
    if (seriesRef.current && data.length) {
      seriesRef.current.setData(data);
      chartRef.current?.timeScale().fitContent();
    }
  }, [data]);

  return (
    <div
      ref={containerRef}
      className={`w-full ${className}`}
      style={{ height }}
    />
  );
}
