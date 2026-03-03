/**
 * OpenClaw API client for ClawBot Panel.
 * All /openclaw/* endpoints: macro, swarm-status, candidates, spawn-team, macro/override, llm-flow WS.
 */
import { getApiUrl } from "../config/api";

const BASE = () => getApiUrl("openclaw");

function getWsBaseUrl() {
  const url = getApiUrl("openclaw");
  return url
    ? url.replace(/^http/, "ws")
    : "ws://localhost:8000/api/v1/openclaw";
}

export async function getMacro() {
  const res = await fetch(`${BASE()}/macro`, { cache: "no-store" });
  if (!res.ok) throw new Error(`OpenClaw macro: ${res.status}`);
  return res.json();
}

export async function getSwarmStatus() {
  const res = await fetch(`${BASE()}/swarm-status`, { cache: "no-store" });
  if (!res.ok) throw new Error(`OpenClaw swarm-status: ${res.status}`);
  return res.json();
}

export async function getCandidates(n = 20) {
  const res = await fetch(`${BASE()}/top?n=${n}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`OpenClaw top: ${res.status}`);
  const data = await res.json();
  return data?.candidates ?? [];
}

export async function spawnTeam(teamType, action) {
  const params = new URLSearchParams({ team_type: teamType, action });
  const res = await fetch(`${BASE()}/spawn-team?${params}`, { method: "POST" });
  if (!res.ok) {
    const err = new Error(`OpenClaw spawn-team: ${res.status}`);
    try {
      err.body = await res.json();
    } catch {
      err.body = null;
    }
    throw err;
  }
  return res.json();
}

export async function setBiasOverride(biasMultiplier) {
  const params = new URLSearchParams({
    bias_multiplier: String(biasMultiplier),
  });
  const res = await fetch(`${BASE()}/macro/override?${params}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = new Error(`OpenClaw macro/override: ${res.status}`);
    try {
      err.body = await res.json();
    } catch {
      err.body = null;
    }
    throw err;
  }
  return res.json();
}

export async function getConsensus() {
  const res = await fetch(`${BASE()}/consensus`, { cache: "no-store" });
  if (!res.ok) throw new Error(`OpenClaw consensus: ${res.status}`);
  const data = await res.json();
  return data?.consensus ?? [];
}

export async function nlpSpawn(prompt) {
  const res = await fetch(`${BASE()}/nlp-spawn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const err = new Error(`OpenClaw nlp-spawn: ${res.status}`);
    try { err.body = await res.json(); } catch { err.body = null; }
    throw err;
  }
  return res.json();
}

export async function getHealthMatrix() {
  const res = await fetch(`${BASE()}/health-matrix`, { cache: "no-store" });
  if (!res.ok) throw new Error(`OpenClaw health-matrix: ${res.status}`);
  return res.json();
}

export function getLlmFlowWsUrl() {
  return `${getWsBaseUrl()}/llm-flow`;
}

export default {
  getMacro,
  getSwarmStatus,
  getCandidates,
  spawnTeam,
  setBiasOverride,
  getLlmFlowWsUrl,
    getConsensus,
  nlpSpawn,
  getHealthMatrix,
};
