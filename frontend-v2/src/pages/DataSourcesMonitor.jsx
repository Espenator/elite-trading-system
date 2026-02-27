import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import {
  Activity,
  Database,
  Server,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Globe,
  Shield,
  Zap,
  Layers,
  FileText,
  TrendingUp,
  TrendingDown,
  Wifi,
  WifiOff,
  MessageSquare,
  Newspaper,
  MessageCircle,
  Brain,
} from "lucide-react";

import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";

const TYPE_ICONS = {
  SCREENER: <Activity className="w-5 h-5 text-blue-400" />,
  OPTIONS_FLOW: <Zap className="w-5 h-5 text-yellow-400" />,
  MARKET_DATA: <TrendingUp className="w-5 h-5 text-green-400" />,
  MACRO: <Globe className="w-5 h-5 text-purple-400" />,
  FILINGS: <FileText className="w-5 h-5 text-slate-400" />,
  SENTIMENT: <MessageSquare className="w-5 h-5 text-pink-400" />,
  NEWS: <Newspaper className="w-5 h-5 text-orange-400" />,
  SOCIAL: <MessageCircle className="w-5 h-5 text-indigo-400" />,
  KNOWLEDGE: <Brain className="w-5 h-5 text-cyan-400" />,
};

// Map API source id (1–10) or fallback id to /data-sources image filename (no extension)
const DATA_SOURCE_IMAGE_SLUGS = {
  1: "finviz",
  2: "unusual_whales",
  3: "alpaca",
  4: "fred",
  5: "sec_edgar",
  6: "stockgeist",
  7: "news_api",
  8: "discord",
  9: "twitter",
  10: "youtube",
  // Fallback when API returns string ids
  alpaca: "alpaca",
  finviz: "finviz",
  fred: "fred",
  sec: "sec_edgar",
  sec_edgar: "sec_edgar",
  stockgeist: "stockgeist",
  newsapi: "news_api",
  news_api: "news_api",
  discord: "discord",
  twitter: "twitter",
  youtube: "youtube",
  unusual_whales: "unusual_whales",
  polygon: null, // no image
};

// Normalize API source name to slug for image lookup
function sourceNameToSlug(name) {
  if (!name) return null;
  const s = name.replace(/\s*\([^)]*\)\s*/g, "").replace(/\s+/g, "_").toLowerCase();
  const nameMap = {
    finviz: "finviz",
    unusual_whales: "unusual_whales",
    alpaca: "alpaca",
    fred: "fred",
    sec_edgar: "sec_edgar",
    stockgeist: "stockgeist",
    news_api: "news_api",
    discord: "discord",
    x: "twitter",
    x_twitter: "twitter",
    twitter: "twitter",
    youtube: "youtube",
  };
  return nameMap[s] || null;
}

function getDataSourceIcon(source) {
  const slug =
    DATA_SOURCE_IMAGE_SLUGS[source.id] ?? sourceNameToSlug(source.name);
  if (slug) {
    return (
      <img
        src={`/data-sources/${slug}.png`}
        alt={source.name}
        className="w-8 h-8 object-contain shrink-0"
      />
    );
  }
  const typeKey = (source.type ?? "").toUpperCase().replace(/\s+/g, "_");
  return TYPE_ICONS[typeKey] || <Database className="w-5 h-5" />;
}

export default function DataSourcesMonitor() {
  const { data: sources, loading, error, refresh } = useApi("dataSources");
  const [openClawStatus, setOpenClawStatus] = useState(null);
  const [wsConnected, setWsConnected] = useState(ws.isConnected());
  const [reconnectCount, setReconnectCount] = useState(0);
  const [lastHeartbeat, setLastHeartbeat] = useState(new Date());

  // --- V3 Simulated History Data for Sparklines ---
  // In a real app, this would come from a timeseries DB endpoint
  const generateHistory = (baseLatency) =>
    Array.from({ length: 20 }).map((_, i) => ({
      time: i,
      latency: Math.max(
        10,
        baseLatency + (0.5 * 20 - 10) + (i === 15 ? 100 : 0),
      ),
    }));

  useEffect(() => {
    // Poll OpenClaw Health
    const fetchOpenClaw = async () => {
      try {
        // Mocked response for now, replace with actual fetch to OpenClaw URL
        const mockResponse = {
          status: "connected",
          lastScan: new Date().toISOString(),
          candidatesFound: 142,
          cacheAge: "12s",
          throughput: 450, // records/min
        };
        setOpenClawStatus(mockResponse);
      } catch (err) {
        console.error("OpenClaw health check failed", err);
        setOpenClawStatus({ status: "error" });
      }
    };

    fetchOpenClaw();
    const interval = setInterval(() => {
      refresh();
      fetchOpenClaw();
    }, 30000); // 30s polling

    // WebSocket Listeners
    const handleWsOpen = () => {
      setWsConnected(true);
      setLastHeartbeat(new Date());
    };
    const handleWsClose = () => {
      setWsConnected(false);
      setReconnectCount((prev) => prev + 1);
    };

    // Subscribe to datasource updates if your WS service supports it
    // ws.subscribe('datasources', (data) => console.log('Live Update:', data));

    // WS connection monitoring (mocking event listeners if service doesn't expose them directly)
    // Assuming ws service has some event mechanism or we check status
    const wsCheck = setInterval(() => {
      const isConn = ws.isConnected();
      if (isConn !== wsConnected) {
        setWsConnected(isConn);
        if (!isConn) setReconnectCount((prev) => prev + 1);
      }
      if (isConn) setLastHeartbeat(new Date());
    }, 5000);

    return () => {
      clearInterval(interval);
      clearInterval(wsCheck);
    };
  }, [refresh, wsConnected]);

  // Helper: Status Colors
  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case "healthy":
        return "text-green-400 bg-green-500/10 border-green-500/30";
      case "degraded":
        return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30";
      case "error":
        return "text-red-400 bg-red-500/10 border-red-500/30";
      default:
        return "text-slate-400 bg-slate-500/10 border-slate-500/30";
    }
  };

  const getLatencyColor = (ms) => {
    if (ms < 100) return "#4ade80"; // Green
    if (ms < 500) return "#facc15"; // Yellow
    return "#ef4444"; // Red
  };

  // Simulated Global Health Score
  const systemHealthScore = 94;
  const healthData = [
    { name: "Health", value: systemHealthScore, color: "#22c55e" },
    { name: "Risk", value: 100 - systemHealthScore, color: "#1e293b" },
  ];

  // Enhanced Source List (Merging API data with V3 metrics)
  // If API is loading/empty, use this structural skeleton
  const enhancedSources = sources?.length
    ? sources
    : [
        {
          id: "alpaca",
          name: "Alpaca Markets",
          type: "MARKET_DATA",
          status: "healthy",
          latency: 45,
          uptime: 99.9,
          records: "12.4M",
          throughput: 850,
          trend: "up",
        },
        {
          id: "polygon",
          name: "Polygon.io",
          type: "OPTIONS_FLOW",
          status: "healthy",
          latency: 112,
          uptime: 99.5,
          records: "4.2M",
          throughput: 1240,
          trend: "stable",
        },
        {
          id: "fred",
          name: "FRED Macro",
          type: "MACRO",
          status: "healthy",
          latency: 320,
          uptime: 99.0,
          records: "850K",
          throughput: 12,
          trend: "stable",
        },
        {
          id: "sec",
          name: "SEC EDGAR",
          type: "FILINGS",
          status: "degraded",
          latency: 850,
          uptime: 96.5,
          records: "1.1M",
          throughput: 45,
          trend: "down",
        },
        {
          id: "twitter",
          name: "X / Twitter",
          type: "SOCIAL",
          status: "healthy",
          latency: 180,
          uptime: 98.2,
          records: "25M",
          throughput: 2100,
          trend: "up",
        },
        {
          id: "newsapi",
          name: "News API",
          type: "NEWS",
          status: "healthy",
          latency: 240,
          uptime: 98.8,
          records: "5.6M",
          throughput: 150,
          trend: "stable",
        },
      ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
        <PageHeader
          icon={Server}
          title="Data Sources Monitor"
          description="Real-time Latency, Throughput & Health Status"
        >
          <div className="flex items-center gap-4">
            <div className="bg-slate-900/50 px-4 py-2 rounded-lg border border-slate-700/50 flex items-center gap-3">
              {wsConnected ? (
                <Wifi className="w-4 h-4 text-green-400" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <div className="flex flex-col">
                <span
                  className={`text-xs font-bold ${wsConnected ? "text-green-400" : "text-red-400"}`}
                >
                  WS {wsConnected ? "CONNECTED" : "DISCONNECTED"}
                </span>
                <span className="text-[10px] text-slate-500">
                  {wsConnected
                    ? `Ping: ${new Date().getSeconds()}ms`
                    : `Retries: ${reconnectCount}`}
                </span>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={refresh}
              disabled={loading}
              leftIcon={RefreshCw}
              className={loading ? "[&>svg]:animate-spin" : ""}
            >
              Refresh
            </Button>
          </div>
        </PageHeader>
      </div>

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        {/* System Health Gauge */}
        <Card className="bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-4 flex items-center justify-between relative overflow-hidden">
          <div>
            <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">
              System Health
            </div>
            <div className="text-3xl font-black text-white">
              {systemHealthScore}%
            </div>
            <div className="text-xs text-green-400 mt-1 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> All Critical Systems
            </div>
          </div>
          <div className="h-20 w-20 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={healthData}
                  cx="50%"
                  cy="50%"
                  innerRadius={25}
                  outerRadius={35}
                  startAngle={90}
                  endAngle={-270}
                  dataKey="value"
                  stroke="none"
                >
                  {healthData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <Activity className="w-5 h-5 text-green-400 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
          </div>
        </Card>

        {/* OpenClaw Status */}
        <Card className="lg:col-span-2 bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg border border-blue-500/30">
                <Database className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">
                  OpenClaw Bridge
                </h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span
                    className={`w-2 h-2 rounded-full ${openClawStatus?.status === "connected" ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
                  ></span>
                  <span className="text-xs text-slate-400 capitalize">
                    {openClawStatus?.status || "Connecting..."}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-white">
                {openClawStatus?.candidatesFound || 0}
              </div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                Candidates
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-700/50">
            <div>
              <div className="text-[10px] text-slate-500">Throughput</div>
              <div className="text-sm font-bold text-blue-400 flex items-center gap-1">
                {openClawStatus?.throughput || 0}{" "}
                <span className="text-[9px] text-slate-600">rec/min</span>
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500">Last Scan</div>
              <div className="text-sm font-bold text-slate-300">
                {openClawStatus?.lastScan
                  ? new Date(openClawStatus.lastScan).toLocaleTimeString()
                  : "--:--"}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500">Cache Age</div>
              <div className="text-sm font-bold text-green-400">
                {openClawStatus?.cacheAge || "0s"}
              </div>
            </div>
          </div>
        </Card>

        {/* Global Throughput */}
        <Card className="bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-4 flex flex-col justify-center items-center">
          <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
            Global Ingestion
          </div>
          <div className="text-4xl font-black text-white mb-1">4.2K</div>
          <div className="text-xs text-slate-500 mb-4">Records / Minute</div>
          <div className="w-full h-10">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Array.from({ length: 10 }).map((_, i) => ({
                  val: 0.5 * 100,
                }))}
              >
                <Bar
                  dataKey="val"
                  fill="#3b82f6"
                  radius={[2, 2, 0, 0]}
                  opacity={0.6}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Main Sources Grid */}
      <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        <Layers className="w-5 h-5 text-purple-500" /> Active Connections
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {enhancedSources.map((source) => (
          <Card
            key={source.id}
            className="bg-slate-800/40 border-slate-700/50 backdrop-blur-sm p-0 overflow-hidden group hover:border-slate-600/50 transition-all"
          >
            {/* Card Header */}
            <div className="p-4 border-b border-slate-700/50 flex justify-between items-start bg-slate-900/30">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-800 rounded-lg border border-slate-700 text-slate-300 group-hover:text-white transition-colors flex items-center justify-center">
                  {getDataSourceIcon(source)}
                </div>
                <div>
                  <h3 className="font-bold text-slate-200 text-sm">
                    {source.name}
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 ${getStatusColor(source.status)}`}
                    >
                      {source.status.toUpperCase()}
                    </Badge>
                    <span className="text-[10px] text-slate-500">
                      ID: {source.id}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs font-bold text-slate-400">Uptime</div>
                <div className="text-sm font-bold text-green-400">
                  {source.uptime || 99.9}%
                </div>
              </div>
            </div>

            {/* Metrics Body */}
            <div className="p-4 grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-slate-500 mb-1">
                  Latency (ms)
                </div>
                <div className="flex items-baseline gap-2">
                  <span
                    className="text-xl font-bold text-white"
                    style={{ color: getLatencyColor(source.latency) }}
                  >
                    {source.latency}
                  </span>
                  <span className="text-[10px] text-slate-500">avg</span>
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 mb-1">Records</div>
                <div className="text-xl font-bold text-white">
                  {source.records || "0"}
                </div>
              </div>
            </div>

            {/* Sparkline & Throughput Footer */}
            <div className="h-16 w-full relative border-t border-slate-700/30 bg-slate-900/20">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={generateHistory(source.latency)}>
                  <defs>
                    <linearGradient
                      id={`grad-${source.id}`}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor={getLatencyColor(source.latency)}
                        stopOpacity={0.2}
                      />
                      <stop
                        offset="95%"
                        stopColor={getLatencyColor(source.latency)}
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="latency"
                    stroke={getLatencyColor(source.latency)}
                    strokeWidth={2}
                    fill={`url(#grad-${source.id})`}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>

              {/* Overlay Metrics */}
              <div className="absolute bottom-2 right-4 text-xs font-bold text-slate-400 flex items-center gap-1 bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700/50">
                {source.throughput || 0} r/m
                {source.trend === "up" ? (
                  <TrendingUp className="w-3 h-3 text-green-400" />
                ) : source.trend === "down" ? (
                  <TrendingDown className="w-3 h-3 text-red-400" />
                ) : (
                  <Activity className="w-3 h-3 text-slate-500" />
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Footer Info */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-slate-900/40 border-slate-700/50 p-4 flex items-center gap-4">
          <Globe className="w-8 h-8 text-purple-500 opacity-50" />
          <div>
            <h4 className="font-bold text-white text-sm">FRED Macro Data</h4>
            <p className="text-xs text-slate-400">
              Syncs daily at 08:00 EST. Tracks GDP, CPI, and Unemployment.
            </p>
          </div>
        </Card>
        <Card className="bg-slate-900/40 border-slate-700/50 p-4 flex items-center gap-4">
          <FileText className="w-8 h-8 text-slate-500 opacity-50" />
          <div>
            <h4 className="font-bold text-white text-sm">SEC EDGAR Filings</h4>
            <p className="text-xs text-slate-400">
              Polling active. 13F, 8K, and Form 4 processed every 15m.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
