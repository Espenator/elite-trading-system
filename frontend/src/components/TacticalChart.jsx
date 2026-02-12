import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

export default function TacticalChart({ symbol }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const [timeframe, setTimeframe] = useState('1H');
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const oldestTimestampRef = useRef(null);
  const allDataRef = useRef([]);

  // Load more historical data
  const loadMoreData = useCallback(async () => {
    if (isLoadingMore || !oldestTimestampRef.current || !symbol) return;
    
    setIsLoadingMore(true);
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';
      const url = `${base.replace(/\/api\/v1$/, '')}/api/v1/chart/data/${symbol}?timeframe=${timeframe}&before=${oldestTimestampRef.current}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      
      const data = await res.json();
      if (data && data.data && data.data.length > 0) {
        // Prepend new data to existing data
        const newData = [...data.data, ...allDataRef.current];
        allDataRef.current = newData;
        oldestTimestampRef.current = newData[0]?.time;
        
        // Update chart
        if (candleSeriesRef.current && volumeSeriesRef.current) {
          const candleData = newData.map((d) => ({
            time: d.time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
          }));
          const volumeData = newData.map((d) => ({
            time: d.time,
            value: d.volume,
            color: d.close >= d.open ? '#00D9FF33' : '#FF006E33',
          }));
          candleSeriesRef.current.setData(candleData);
          volumeSeriesRef.current.setData(volumeData);
        }
      }
    } catch (err) {
      console.error('Error loading more data:', err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [symbol, timeframe, isLoadingMore]);

  // Fetch chart data from backend
  useEffect(() => {
    if (!symbol) return;
    
    const abortController = new AbortController();
    
    setChartData(null);
    setIsLoading(true);
    allDataRef.current = [];
    oldestTimestampRef.current = null;
    
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';
    const url = `${base.replace(/\/api\/v1$/, '')}/api/v1/chart/data/${symbol}?timeframe=${timeframe}`;
    
    fetch(url, { signal: abortController.signal })
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        if (data && data.data && data.data.length > 0) {
          allDataRef.current = data.data;
          oldestTimestampRef.current = data.data[0]?.time;
          setChartData(data);
          setIsLoading(false);
        } else {
          console.warn('No chart data received');
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Chart data error:', err);
        }
        setIsLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [symbol, timeframe]);

  // Create chart once
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#0a0e1a' },
        textColor: '#7B8CA6',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: '#1a1f2e' },
        horzLines: { color: '#1a1f2e' },
      },
      crosshair: {
        mode: 1,
      },
      timeScale: {
        borderColor: '#2B3139',
        timeVisible: true,
        secondsVisible: false,
        shiftVisibleRangeOnNewBar: true,
        rightOffset: 5,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
      rightPriceScale: {
        borderColor: '#2B3139',
      },
    });

    chartRef.current = chart;

    // Add candlestick series (v5 API)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#00D9FF',
      downColor: '#FF006E',
      borderUpColor: '#00D9FF',
      borderDownColor: '#FF006E',
      wickUpColor: '#00D9FF',
      wickDownColor: '#FF006E',
    });
    candleSeriesRef.current = candleSeries;

    // Add volume series (v5 API)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });
    volumeSeriesRef.current = volumeSeries;

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  // Handle visible range change to load more data when scrolling left
  useEffect(() => {
    if (!chartRef.current || !chartData) return;

    const handleVisibleRangeChange = () => {
      if (!chartRef.current || !oldestTimestampRef.current || isLoadingMore) return;
      
      const visibleRange = chartRef.current.timeScale().getVisibleLogicalRange();
      if (!visibleRange) return;
      
      // If user scrolled near the left edge (within 10 bars), load more data
      if (visibleRange.from < 10) {
        loadMoreData();
      }
    };

    chartRef.current.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);

    return () => {
      if (chartRef.current) {
        chartRef.current.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
      }
    };
  }, [chartData, loadMoreData, isLoadingMore]);

  // Update chart data when it changes
  useEffect(() => {
    if (!chartData || !candleSeriesRef.current || !volumeSeriesRef.current) return;

    const candleData = chartData.data.map((d) => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    const volumeData = chartData.data.map((d) => ({
      time: d.time,
      value: d.volume,
      color: d.close >= d.open ? '#00D9FF33' : '#FF006E33',
    }));

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);

    // Fit content to view
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [chartData]);

  return (
    <div className="tactical-chart-container">
      <div className="chart-header">
        <h2 className="chart-title">{symbol} - Tactical Chart</h2>
        <div className="timeframe-selector">
          {['5m', '15m', '1H', '4H', '1D'].map(tf => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-area">
        <div 
          ref={chartContainerRef} 
          className="chart-content"
          style={{ width: '100%', height: '100%', position: 'relative' }}
        >
          {(isLoading || !chartData) && (
            <div className="chart-loading-overlay" style={{ 
              position: 'absolute', 
              inset: 0, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              zIndex: 10,
              background: 'rgba(10, 14, 26, 0.85)'
            }}>
              <div className="loading-spinner" style={{
                width: '40px',
                height: '40px',
                border: '3px solid rgba(0, 217, 255, 0.2)',
                borderTop: '3px solid #00D9FF',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              <style>{`
                @keyframes spin {
                  0% { transform: rotate(0deg); }
                  100% { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          )}
          {isLoadingMore && (
            <div style={{
              position: 'absolute',
              top: '10px',
              left: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              background: 'rgba(0, 217, 255, 0.15)',
              borderRadius: '4px',
              zIndex: 10
            }}>
              <div style={{
                width: '14px',
                height: '14px',
                border: '2px solid rgba(0, 217, 255, 0.3)',
                borderTop: '2px solid #00D9FF',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              <span style={{ color: '#00D9FF', fontSize: '12px' }}>Loading history...</span>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

