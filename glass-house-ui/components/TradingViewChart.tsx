'use client';

import { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';
import { useEliteStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export default function TradingViewChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  
  const { selectedTicker, timeframe } = useEliteStore();

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0A0E1A' },
        textColor: '#94A3B8',
      },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: 'rgba(148, 163, 184, 0.2)',
      },
      rightPriceScale: {
        borderColor: 'rgba(148, 163, 184, 0.2)',
      },
    });

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderUpColor: '#10B981',
      borderDownColor: '#EF4444',
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Fetch and update chart data when ticker or timeframe changes
  useEffect(() => {
    const fetchChartData = async () => {
      try {
        const intervalMap = {
          '5M': '5m',
          '15M': '15m',
          '1H': '1h',
          '1D': '1d',
        };

        const data = await apiClient.getChartData(
          selectedTicker,
          intervalMap[timeframe]
        );

        if (candlestickSeriesRef.current && data.length > 0) {
          candlestickSeriesRef.current.setData(data);
        }
      } catch (error) {
        console.error('Failed to fetch chart data:', error);
      }
    };

    fetchChartData();
  }, [selectedTicker, timeframe]);

  return (
    <div 
      ref={chartContainerRef} 
      className="w-full h-full"
      style={{ minHeight: '400px' }}
    />
  );
}
