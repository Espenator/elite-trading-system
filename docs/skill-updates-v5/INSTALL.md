# Cowork Skill Updates — v5.0.0

These updated SKILL.md files replace the stale v4.1.0-dev versions in your Cowork skills.

## Installation

On Windows, copy each file to your Cowork skills directory:

```powershell
# From repo root:
$skillsDir = "$env:APPDATA\Claude\local-agent-mode-sessions\skills-plugin"

# Find the actual skills subdirectory (UUID-based)
$skillsPath = Get-ChildItem -Path $skillsDir -Recurse -Filter "embodier-second-brain" -Directory | Select-Object -First 1

# If found, copy the updated files
if ($skillsPath) {
    $base = $skillsPath.Parent.FullName
    Copy-Item "docs\skill-updates-v5\embodier-second-brain-SKILL.md" "$base\embodier-second-brain\SKILL.md" -Force
    Copy-Item "docs\skill-updates-v5\embodier-trader-SKILL.md" "$base\embodier-trader\SKILL.md" -Force
    Copy-Item "docs\skill-updates-v5\agent-swarm-design-SKILL.md" "$base\agent-swarm-design\SKILL.md" -Force
    Write-Host "Skills updated to v5.0.0!"
} else {
    Write-Host "Skills directory not found. Manually copy files to your Cowork skills folder."
}
```

## What Changed

| Skill | Old Version | Key Updates |
|-------|------------|-------------|
| embodier-second-brain | v4.1.0-dev (referenced IndentationErrors blocker, 22 tests, no auth) | v5.0.0: 982+ tests, CI GREEN, 35-agent DAG, Bearer auth, all phases complete |
| embodier-trader | v4.1.0-dev (25 routes, 15 services, backend never run) | v5.0.0: 43 routes, 72+ services, full pipeline operational |
| agent-swarm-design | Generic OpenClaw blackboard (abstract patterns) | v5.0.0: Actual 7-stage council DAG, MessageBus, Bayesian learning, VETO rules |
