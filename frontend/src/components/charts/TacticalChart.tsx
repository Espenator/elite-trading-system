// frontend/src/components/charts/TacticalChart.tsx
'use client';

import React, { useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  Time
} from 'lightweight-charts';
import { useTradingStore } from '@/lib/store';
import { OHLCV } from '@/lib/types';

interface TacticalChartProps {
  symbol: string;
  theme?: 'dark' | 'light';
}

export default function TacticalChart({ symbol, theme = 'dark' }: TacticalChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  // Connect to the brain (Zustand Store)
  const { prices, subscribeToSymbol, unsubscribeFromSymbol } = useTradingStore();

  // Color Palette - Bloomberg Terminal Style
  const colors = {
    background: theme === 'dark' ? '#0f172a' : '#ffffff', // slate-950
    text: theme === 'dark' ? '#94a3b8' : '#333333', // slate-400
    grid: theme === 'dark' ? '#1e293b' : '#f0f0f0', // slate-800
    upColor: '#10b981', // emerald-500
    downColor: '#ef4444', // red-500
    wickUp: '#10b981',
    wickDown: '#ef4444',
  };

  // 1. Initialize Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Add Candlestick Series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: colors.upColor,
      downColor: colors.downColor,
      borderVisible: false,
      wickUpColor: colors.wickUp,
      wickDownColor: colors.wickDown,
    });

    // Add Volume Series (Overlay)
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // Overlay on the same scale
    });

    // Scale volume to sit at bottom 20% of chart
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // --- INITIAL DATA LOAD ---
    // In production, this comes from: await apiClient.getOHLCV(symbol, '1D');
    const initialData: CandlestickData<Time>[] = []; // Replace with fetch
    candlestickSeries.setData(initialData);

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;

    // Handle Resize
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [theme]);

  // 2. Manage Subscriptions
  useEffect(() => {
    subscribeToSymbol(symbol);
    return () => unsubscribeFromSymbol(symbol);
  }, [symbol, subscribeToSymbol, unsubscribeFromSymbol]);

  // 3. Real-Time Updates from Store
  useEffect(() => {
    const latestTick = prices[symbol];
    if (!latestTick || !candlestickSeriesRef.current) return;

    // Convert Tick to Candle Update
    // In a real app, you'd aggregate ticks into the current open candle.
    // Here we update the "current" candle's close price.

    // NOTE: This logic assumes we have the LAST candle and we are updating it.
    // For full OHLCV aggregation, we need the `currentCandle` state from the store.

    // Example: Updating the latest bar
    // candlestickSeriesRef.current.update({
    //   time: latestTick.timestamp as Time,
    //   open: ...,
    //   high: ...,
    //   low: ...,
    //   close: latestTick.price
    // });

  }, [prices, symbol]);

  return (
    <div className="w-full h-full relative group">
      <div
        ref={chartContainerRef}
        className="w-full h-[500px] rounded-lg overflow-hidden border border-slate-800 shadow-2xl"
      />

      {/* Loading Overlay */}
      {(!chartRef.current) && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 z-10">
          <span className="text-blue-500 font-mono animate-pulse">Initializing Neural Canvas...</span>
        </div>
      )}
    </div>
  );
}
