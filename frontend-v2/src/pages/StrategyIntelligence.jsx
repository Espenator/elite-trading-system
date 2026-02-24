import React, { useState, useEffect } from "react";
import { Target } from "lucide-react";
import Card from "../components/ui/Card";
import Toggle from "../components/ui/Toggle";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

const StrategyIntelligence = () => {
  const { data, loading, error, refetch } = useApi("strategy", {
    pollIntervalMs: 30000,
  });
  const strategies = Array.isArray(data?.strategies) ? data.strategies : [];
  const [masterSwitch, setMasterSwitch] = useState(
    data?.controls?.masterSwitch ?? true,
  );
  const [pauseAll, setPauseAll] = useState(data?.controls?.pauseAll ?? false);
  const [closeAllPositions, setCloseAllPositions] = useState(
    data?.controls?.closeAllPositions ?? false,
  );
  const [saving, setSaving] = useState(false);

  // Sync state when API data loads
  useEffect(() => {
    if (data?.controls) {
      setMasterSwitch(data.controls.masterSwitch ?? true);
      setPauseAll(data.controls.pauseAll ?? false);
      setCloseAllPositions(data.controls.closeAllPositions ?? false);
    }
  }, [data]);

  const saveControls = async (updates) => {
    setSaving(true);
    try {
      const response = await fetch(`${getApiUrl("strategy")}/controls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error("Failed to save");
      await refetch();
    } catch (err) {
      console.error("Failed to save controls:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleMasterSwitch = (checked) => {
    setMasterSwitch(checked);
    saveControls({ masterSwitch: checked });
  };

  const handlePauseAll = (checked) => {
    setPauseAll(checked);
    saveControls({ pauseAll: checked });
  };

  const handleCloseAll = (checked) => {
    setCloseAllPositions(checked);
    saveControls({ closeAllPositions: checked });
  };

  const getStatusVariant = (status) => {
    switch (status) {
      case "Active":
        return "success";
      case "Paused":
        return "warning";
      case "Error":
        return "danger";
      default:
        return "secondary";
    }
  };

  const getStatusBorder = (status) => {
    switch (status) {
      case "Active":
        return "border-success/50";
      case "Paused":
        return "border-warning/50";
      case "Error":
        return "border-danger/50";
      default:
        return "border-secondary/50";
    }
  };

  return (
    <div className="min-h-full bg-dark text-white space-y-6">
      <PageHeader
        icon={Target}
        title="Strategy Intelligence"
        description={
          error
            ? "Failed to load strategies"
            : saving
              ? "Saving..."
              : "Manage strategies and emergency controls"
        }
      >
        {error && (
          <span className="text-xs text-danger font-medium">
            Failed to load
          </span>
        )}
        {saving && (
          <span className="text-xs text-primary font-medium">Saving...</span>
        )}
      </PageHeader>
      <Card
        title="Emergency Controls"
        subtitle="Global settings to manage all active strategies and positions."
        className="mb-6"
      >
        <div className="space-y-4">
          <Toggle
            label="Master Switch (ON/OFF)"
            checked={masterSwitch}
            onChange={handleMasterSwitch}
          />
          <Toggle
            label="Pause All Strategies"
            checked={pauseAll}
            onChange={handlePauseAll}
          />
          <Toggle
            label="Close All Positions"
            description="Danger: closes all open positions"
            checked={closeAllPositions}
            onChange={handleCloseAll}
          />
        </div>
      </Card>

      {loading && strategies.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="h-6 bg-secondary/20 rounded w-2/3 mb-4" />
              <div className="h-4 bg-secondary/20 rounded w-full mb-2" />
              <div className="h-4 bg-secondary/20 rounded w-3/4" />
            </Card>
          ))}
        </div>
      )}
      {error && strategies.length === 0 && (
        <Card className="p-6 text-center">
          <p className="text-secondary mb-2">
            Could not load strategies. Check GET /api/v1/strategy.
          </p>
          <Button variant="outline" size="sm" onClick={refetch}>
            Retry
          </Button>
        </Card>
      )}
      {!loading && strategies.length === 0 && !error && (
        <Card className="p-6 text-center">
          <p className="text-secondary">No strategies configured yet.</p>
        </Card>
      )}
      {!loading && strategies.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">My Trading Strategies</h2>
            <Button variant="primary">+ Add New Strategy</Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {strategies.map((strategy) => (
              <Card
                key={strategy.id}
                className={`border-2 ${getStatusBorder(strategy.status)}`}
                noPadding
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-bold mb-1 text-white">
                        {strategy.name}
                      </h3>
                      <Badge variant={getStatusVariant(strategy.status)}>
                        ▶ {strategy.status}
                      </Badge>
                    </div>
                  </div>

                  <p className="text-sm text-secondary mb-4">
                    {strategy.description}
                  </p>

                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div>
                      <p className="text-xs text-secondary mb-1">Daily P&L</p>
                      <p
                        className={`text-lg font-bold ${strategy.dailyPL >= 0 ? "text-success" : "text-danger"}`}
                      >
                        {strategy.dailyPL >= 0 ? "+" : ""}
                        {strategy.dailyPL}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-secondary mb-1">Win Rate</p>
                      <p className="text-lg font-bold text-white">
                        {strategy.winRate}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-secondary mb-1">
                        Max Drawdown
                      </p>
                      <p className="text-lg font-bold text-danger">
                        {strategy.maxDrawdown}%
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Button variant="secondary" className="flex-1">
                      View Details
                    </Button>
                    <Button variant="secondary" className="flex-1">
                      Edit
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default StrategyIntelligence;
