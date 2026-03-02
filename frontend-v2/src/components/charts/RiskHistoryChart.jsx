import React, { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";

const MAX_DAILY_LOSS_COLOR = "#22d3ee"; // cyan-400
const VAR_COLOR = "#ec4899"; // pink-500

/**
 * Historical Risk Metrics: Max Daily Loss (%) and VaR ($) over time.
 * Uses TradingView Lightweight Charts. Expects data from API: { date, maxDailyLoss, var }[].
 * Shows empty state when data is missing or empty.
 */
export default function RiskHistoryChart({ data = [], className = "" }) {
  const hasData = Array.isArray(data) && data.length > 0;
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current || !hasData) return;
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#334155", style: 1 },
        horzLines: { color: "#334155", style: 1 },
      },
      width: chartContainerRef.current.clientWidth,
      height: 256,
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.1 } },
      leftPriceScale: { visible: true, borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderVisible: false },
      crosshair: {
        vertLine: { labelVisible: true },
        horzLine: { labelVisible: true },
      },
    });

    // Max Daily Loss (%) on left price scale
    const lossSeries = chart.addLineSeries({
      color: MAX_DAILY_LOSS_COLOR,
      lineWidth: 2,
      priceScaleId: "left",
      title: "Max Daily Loss (%)",
    });
    lossSeries.setData(
      data
        .map((d) => ({
          time: d.date ? Math.floor(new Date(d.date).getTime() / 1000) : null,
          value: d.maxDailyLoss != null ? Number(d.maxDailyLoss) : null,
        }))
        .filter((d) => d.time != null && d.value != null)
        .sort((a, b) => a.time - b.time)
    );

    // VaR ($) on right price scale
    const varSeries = chart.addLineSeries({
      color: VAR_COLOR,
      lineWidth: 2,
      priceScaleId: "right",
      title: "VaR ($)",
    });
    varSeries.setData(
      data
        .map((d) => ({
          time: d.date ? Math.floor(new Date(d.date).getTime() / 1000) : null,
          value: d.var != null ? Number(d.var) : null,
        }))
        .filter((d) => d.time != null && d.value != null)
        .sort((a, b) => a.time - b.time)
    );

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [data, hasData]);

  if (!hasData) {
    return (
      <div
        className={`flex flex-col items-center justify-center rounded-xl border border-cyan-500/10 bg-secondary/10 ${className}`}
        style={{ minHeight: 256 }}
      >
        <p className="text-sm text-secondary">No risk history data</p>
        <p className="text-xs text-secondary/80 mt-1">
          Max Daily Loss and VaR over time
        </p>
      </div>
    );
  }

  return (
    <div className={`overflow-hidden ${className}`}>
      {/* Legend */}
      <div className="flex items-center gap-4 mb-2 px-2">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: MAX_DAILY_LOSS_COLOR }} />
          <span className="text-xs text-secondary">Max Daily Loss (%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: VAR_COLOR }} />
          <span className="text-xs text-secondary">VaR ($)</span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" style={{ height: 256 }} />
    </div>
  );
}
