// CLAWBOT PANEL - Swarm command center (OpenClaw teams, candidates, LLM flow, bias)
// Design: CLAWBOT_PANEL_DESIGN.md

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  Play,
  Square,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
  Zap,
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import * as openclaw from "../services/openclawService";

const LLM_ALERTS_MAX = 5;
const SWARM_POLL_MS = 15000;
const CANDIDATES_POLL_MS = 30000;

function TeamBadge({ teamId }) {
  if (!teamId) return null;
  const label = String(teamId).replace(/_/g, " ");
  const hue =
    (label.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % 12) * 30;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white"
      style={{ backgroundColor: `hsl(${hue}, 55%, 40%)` }}
      title={teamId}
    >
      {label}
    </span>
  );
}

function LlmAlert({ alert, onDismiss }) {
  const severity = alert.severity || "info";
  const isHigh = severity === "high" || severity === "error";
  const isWarning = severity === "warning";
  const bg = isHigh
    ? "bg-danger/15 border-danger/40"
    : isWarning
      ? "bg-warning/15 border-warning/40"
      : "bg-primary/15 border-primary/40";
  return (
    <div
      className={`flex items-start gap-2 p-2 rounded-lg border ${bg} text-sm`}
    >
      {isHigh ? (
        <AlertTriangle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
      ) : (
        <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
      )}
      <span className="flex-1 min-w-0 text-white">
        {alert.message || alert.text || JSON.stringify(alert)}
      </span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-secondary hover:text-white"
        >
          ×
        </button>
      )}
    </div>
  );
}

export default function ClawBotPanel() {
  const navigate = useNavigate();
  const [swarm, setSwarm] = useState({ active: 0, total: 0, teams: [] });
  const [candidates, setCandidates] = useState([]);
  const [bias, setBias] = useState(1.0);
  const [biasOverrideSent, setBiasOverrideSent] = useState(false);
  const [spawnModalOpen, setSpawnModalOpen] = useState(false);
  const [spawnLoading, setSpawnLoading] = useState(false);
  const [spawnError, setSpawnError] = useState(null);
  const [llmAlerts, setLlmAlerts] = useState([]);
  const wsRef = useRef(null);

  const loadSwarm = useCallback(async () => {
    try {
      const data = await openclaw.getSwarmStatus();
      setSwarm({
        active: data.active ?? 0,
        total: data.total ?? 0,
        teams: data.teams ?? [],
      });
    } catch {
      setSwarm({ active: 0, total: 0, teams: [] });
    }
  }, []);

  const loadCandidates = useCallback(async () => {
    try {
      const list = await openclaw.getCandidates(25);
      setCandidates(Array.isArray(list) ? list : []);
    } catch {
      setCandidates([]);
    }
  }, []);

  useEffect(() => {
    loadSwarm();
    const t = setInterval(loadSwarm, SWARM_POLL_MS);
    return () => clearInterval(t);
  }, [loadSwarm]);

  useEffect(() => {
    loadCandidates();
    const t = setInterval(loadCandidates, CANDIDATES_POLL_MS);
    return () => clearInterval(t);
  }, [loadCandidates]);

  useEffect(() => {
    const wsUrl = openclaw.getLlmFlowWsUrl();
    let ws;
    try {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          setLlmAlerts((prev) =>
            [{ ...msg, id: Date.now() + Math.random() }, ...prev].slice(
              0,
              LLM_ALERTS_MAX,
            ),
          );
        } catch {
          setLlmAlerts((prev) => [
            { id: Date.now(), message: ev.data, severity: "info" },
            ...prev.slice(0, LLM_ALERTS_MAX - 1),
          ]);
        }
      };
      ws.onclose = () => {
        wsRef.current = null;
      };
    } catch (e) {
      console.warn("LLM flow WebSocket failed:", e);
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const handleBiasChange = (value) => {
    setBias(value);
    setBiasOverrideSent(false);
  };

  const handleBiasSubmit = async () => {
    try {
      await openclaw.setBiasOverride(bias);
      setBiasOverrideSent(true);
    } catch (e) {
      console.error("Bias override failed:", e);
    }
  };

  const handleSpawnTeam = async (teamType, action) => {
    setSpawnLoading(true);
    setSpawnError(null);
    try {
      await openclaw.spawnTeam(teamType, action);
      await loadSwarm();
    } catch (e) {
      setSpawnError(e.body?.detail || e.message || "Request failed");
    } finally {
      setSpawnLoading(false);
    }
  };

  const handleCandidateClick = (c) => {
    const symbol = c.symbol || c.ticker;
    const entry = c.entry_price ?? c.suggested_entry ?? c.entry ?? 0;
    const stop = c.stop_loss ?? c.suggested_stop ?? c.stop ?? 0;
    const target = c.target_price ?? c.suggested_target ?? c.target ?? 0;
    const team = c.team_id ?? c.team ?? null;
    const score = c.composite_score ?? c.score ?? 0;
    const detail = { symbol, entry, stop, target, team, score };
    window.dispatchEvent(new CustomEvent("openTradeExecution", { detail }));
    navigate("/trades", { state: { openTradeExecution: detail } });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Bot}
        title="Swarm Command Center"
        description="Swarm command center: teams, candidates, and LLM flow alerts."
      />

      {/* Swarm Status bar */}
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => setSpawnModalOpen(!spawnModalOpen)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-secondary/20 border border-secondary/40 text-white hover:bg-secondary/30 font-medium transition-colors"
        >
          <span>
            {swarm.active}/{swarm.total} teams
          </span>
          {spawnModalOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>
        {spawnModalOpen && (
          <Card className="w-full p-4 border-primary/20">
            <h3 className="font-semibold text-white mb-3">
              Operator overrides
            </h3>
            <div className="flex flex-wrap gap-2 mb-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={spawnLoading}
                onClick={() => handleSpawnTeam("fear_bounce_team", "spawn")}
                className="bg-danger/15 text-danger border-danger/40 hover:bg-danger/25"
              >
                <Play className="w-4 h-4 mr-1" />
                Spawn Fear Team
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={spawnLoading}
                onClick={() => handleSpawnTeam("greed_momentum_team", "spawn")}
                className="bg-success/15 text-success border-success/40 hover:bg-success/25"
              >
                <Play className="w-4 h-4 mr-1" />
                Spawn Greed Team
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={spawnLoading}
                onClick={() => handleSpawnTeam("all", "kill")}
              >
                <Square className="w-4 h-4 mr-1" />
                Kill All
              </Button>
            </div>
            <div className="flex items-center gap-3 pt-2 border-t border-secondary/30">
              <Slider
                label="Bias"
                min={0.5}
                max={2}
                step={0.1}
                value={bias}
                onChange={(e) => handleBiasChange(Number(e.target.value))}
                suffix="x"
                formatValue={(v) => Number(v).toFixed(1)}
                className="flex-1 min-w-0 max-w-[180px]"
              />
              <Button variant="primary" size="sm" onClick={handleBiasSubmit}>
                Apply
              </Button>
              {biasOverrideSent && (
                <span className="text-xs text-success">Saved</span>
              )}
            </div>
            {spawnError && (
              <p className="text-sm text-danger mt-2">{spawnError}</p>
            )}
          </Card>
        )}
      </div>

      {/* Candidates Table */}
      <Card
        title="Candidates"
        subtitle="Click a row to open Trade Execution with entry/stop/target."
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-secondary/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
                  Symbol
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
                  Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
                  Team
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
                  Entry
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
                  Stop
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
                  Target
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary/30">
              {candidates.length === 0 ? (
                <tr>
                  <td
                    colSpan="6"
                    className="px-4 py-8 text-center text-secondary"
                  >
                    No candidates. OpenClaw bridge may be idle or not
                    configured.
                  </td>
                </tr>
              ) : (
                candidates.map((c) => {
                  const symbol = c.symbol || c.ticker || "—";
                  const score = c.composite_score ?? c.score ?? 0;
                  const entry =
                    c.entry_price ?? c.suggested_entry ?? c.entry ?? "—";
                  const stop = c.stop_loss ?? c.suggested_stop ?? c.stop ?? "—";
                  const target =
                    c.target_price ?? c.suggested_target ?? c.target ?? "—";
                  const teamId = c.team_id ?? c.team ?? null;
                  return (
                    <tr
                      key={symbol + (c.composite_score ?? "")}
                      onClick={() => handleCandidateClick(c)}
                      className="hover:bg-secondary/20 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 font-medium text-white">
                        {symbol}
                      </td>
                      <td className="px-4 py-3 text-secondary">
                        {Number(score).toFixed(1)}
                      </td>
                      <td className="px-4 py-3">
                        <TeamBadge teamId={teamId} />
                        {!teamId && (
                          <span className="text-secondary text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-secondary">
                        {typeof entry === "number" ? entry.toFixed(2) : entry}
                      </td>
                      <td className="px-4 py-3 text-secondary">
                        {typeof stop === "number" ? stop.toFixed(2) : stop}
                      </td>
                      <td className="px-4 py-3 text-secondary">
                        {typeof target === "number"
                          ? target.toFixed(2)
                          : target}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* LLM Flow alerts */}
      <Card title="LLM Flow" subtitle="Last 5 alerts from WebSocket stream.">
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {llmAlerts.length === 0 ? (
            <p className="text-sm text-secondary">
              Connect to stream for alerts.
            </p>
          ) : (
            llmAlerts.map((a) => (
              <LlmAlert
                key={a.id}
                alert={a}
                onDismiss={() =>
                  setLlmAlerts((prev) => prev.filter((x) => x.id !== a.id))
                }
              />
            ))
          )}
        </div>
      </Card>

      {/* Heatmap mini */}
      <Card
        title="Symbols by score"
        subtitle="Top candidates by composite score."
      >
        <div className="flex flex-wrap gap-2">
          {candidates.slice(0, 15).map((c) => {
            const symbol = c.symbol || c.ticker;
            const score = c.composite_score ?? c.score ?? 0;
            const pct = Math.min(100, Math.max(0, score));
            return (
              <span
                key={symbol}
                className="px-2 py-1 rounded text-xs font-medium text-white"
                style={{
                  backgroundColor: `hsl(${120 - (pct / 100) * 120}, 60%, 40%)`,
                }}
                title={`${symbol}: ${score.toFixed(1)}`}
              >
                {symbol}
              </span>
            );
          })}
          {candidates.length === 0 && (
            <span className="text-sm text-secondary">No symbols</span>
          )}
        </div>
      </Card>
    </div>
  );
}
