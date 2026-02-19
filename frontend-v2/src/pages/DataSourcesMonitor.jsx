import React from "react";
import {
  Activity,
  Database,
  FileText,
  MessageSquare,
  Radio,
  RefreshCw,
  Link2,
  TrendingUp,
  Video,
  Zap,
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

const TYPE_ICONS = {
  Screener: TrendingUp,
  "Options Flow": Zap,
  "Market Data": Activity,
  Macro: Database,
  Filings: FileText,
  Sentiment: MessageSquare,
  News: Radio,
  Social: MessageSquare,
  Knowledge: Video,
};
const DEFAULT_ICON = Link2;

function getStatusVariant(status) {
  switch (status) {
    case "healthy":
      return "success";
    case "degraded":
      return "warning";
    case "error":
      return "danger";
    default:
      return "secondary";
  }
}

function latencyColor(latencyMs) {
  if (latencyMs == null) return "text-secondary";
  if (latencyMs <= 150) return "text-success";
  if (latencyMs <= 500) return "text-warning";
  return "text-danger";
}

const DataSourcesMonitor = () => {
  const { data, loading, error, refetch } = useApi("dataSources", {
    pollIntervalMs: 30000,
  });
  const sources = Array.isArray(data?.sources) ? data.sources : [];

  const stats = React.useMemo(() => {
    const healthy = sources.filter((s) => s.status === "healthy").length;
    const degraded = sources.filter((s) => s.status === "degraded").length;
    const err = sources.filter((s) => s.status === "error").length;
    return { healthy, degraded, error: err, total: sources.length };
  }, [sources]);

  return (
    <div className="min-h-full bg-dark text-white space-y-6">
      <PageHeader
        icon={Link2}
        title="Data Sources Monitor"
        description="Health and latency for all 10 feeds"
      >
        {sources.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1.5 text-success">
              <span className="w-2 h-2 rounded-full bg-success" />
              {stats.healthy} healthy
            </span>
            {stats.degraded > 0 && (
              <span className="flex items-center gap-1.5 text-warning">
                <span className="w-2 h-2 rounded-full bg-warning" />
                {stats.degraded} degraded
              </span>
            )}
            {stats.error > 0 && (
              <span className="flex items-center gap-1.5 text-danger">
                <span className="w-2 h-2 rounded-full bg-danger" />
                {stats.error} error
              </span>
            )}
          </div>
        )}
        {error && (
          <span className="text-xs text-danger font-medium">
            Failed to load
          </span>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={refetch}
          disabled={loading}
          leftIcon={RefreshCw}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </Button>
      </PageHeader>

      {/* Source grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {loading && sources.length === 0 && (
          <>
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Card key={i} noPadding className="overflow-hidden">
                <div className="p-5 animate-pulse">
                  <div className="h-5 bg-secondary/20 rounded w-2/3 mb-3" />
                  <div className="h-3 bg-secondary/20 rounded w-1/3 mb-4" />
                  <div className="grid grid-cols-3 gap-2">
                    <div className="h-8 bg-secondary/20 rounded" />
                    <div className="h-8 bg-secondary/20 rounded" />
                    <div className="h-8 bg-secondary/20 rounded" />
                  </div>
                </div>
              </Card>
            ))}
          </>
        )}

        {sources.length === 0 && !loading && (
          <Card className="col-span-full" noPadding>
            <div className="py-16 px-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-secondary/20 flex items-center justify-center mx-auto mb-4">
                <Server className="w-7 h-7 text-secondary" />
              </div>
              <h2 className="text-lg font-semibold text-white mb-2">
                No data sources
              </h2>
              <p className="text-secondary text-sm max-w-md mx-auto mb-6">
                Start the backend or check GET /api/v1/data-sources to see feed
                health and latency.
              </p>
              <Button variant="secondary" onClick={refetch}>
                Retry
              </Button>
            </div>
          </Card>
        )}

        {sources.map((source) => {
          const Icon = TYPE_ICONS[source.type] || DEFAULT_ICON;
          const statusVariant = getStatusVariant(source.status);
          return (
            <Card
              key={source.id}
              noPadding
              className={`
                overflow-hidden transition-all duration-200
                border-l-4
                ${source.status === "healthy" ? "border-l-success/80" : ""}
                ${source.status === "degraded" ? "border-l-warning/80" : ""}
                ${source.status === "error" ? "border-l-danger/80" : ""}
                ${!["healthy", "degraded", "error"].includes(source.status) ? "border-l-secondary/50" : ""}
                hover:border-secondary/50
              `}
            >
              <div className="p-5">
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`
                      w-10 h-10 rounded-xl flex items-center justify-center shrink-0
                      ${source.status === "healthy" ? "bg-success/15 text-success" : ""}
                      ${source.status === "degraded" ? "bg-warning/15 text-warning" : ""}
                      ${source.status === "error" ? "bg-danger/15 text-danger" : ""}
                      ${!["healthy", "degraded", "error"].includes(source.status) ? "bg-secondary/20 text-secondary" : ""}
                    `}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-white truncate">
                        {source.name}
                      </h3>
                      <p className="text-xs text-secondary mt-0.5">
                        {source.type}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={statusVariant}
                    size="sm"
                    className="shrink-0 capitalize"
                  >
                    <span
                      className={`
                      w-1.5 h-1.5 rounded-full mr-1.5
                      ${source.status === "healthy" ? "bg-success" : ""}
                      ${source.status === "degraded" ? "bg-warning animate-pulse" : ""}
                      ${source.status === "error" ? "bg-danger" : ""}
                    `}
                    />
                    {source.status}
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-3 pt-3 border-t border-secondary/30">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-secondary mb-0.5">
                      Latency
                    </p>
                    <p
                      className={`text-sm font-semibold tabular-nums ${latencyColor(source.latencyMs)}`}
                    >
                      {source.latencyMs != null
                        ? `${source.latencyMs} ms`
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-secondary mb-0.5">
                      Last sync
                    </p>
                    <p className="text-sm font-medium text-white truncate">
                      {source.lastSync || "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-secondary mb-0.5">
                      Records
                    </p>
                    <p className="text-sm font-semibold text-white tabular-nums">
                      {(source.recordCount ?? 0).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* API info */}
      <Card
        title="FRED Macro & SEC EDGAR"
        subtitle="Connect /api/v1/data-sources/fred/regime and /data-sources/edgar/filings for live macro and filings data."
        className="mt-8"
      />
    </div>
  );
};

export default DataSourcesMonitor;
