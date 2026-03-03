<#
  EMBODIER TRADING SYNC — FULLY SELF-CONTAINED INSTALLER
  Paste this into PowerShell (Admin) on BOTH PCs: ESPENMAIN & Profit Trader
  Finds OneDrive, finds/creates Trading folder, finds Python, creates sync engine,
  installs 5-minute scheduled task. Zero dependencies.
#>

$ErrorActionPreference = "Continue"
$TaskName = "EmbodierTradingSync"
$Interval = 5

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "  EMBODIER TRADING SYNC — ONE-CLICK INSTALLER" -ForegroundColor Cyan
Write-Host "  PC: $env:COMPUTERNAME" -ForegroundColor Yellow
Write-Host "================================================`n" -ForegroundColor Cyan

# ═══════════════════════════════════════════════
# 1. FIND ONEDRIVE — search everywhere
# ═══════════════════════════════════════════════
$OneDrive = $null

# Method 1: Environment variables
$envPaths = @($env:OneDriveConsumer, $env:OneDrive, $env:OneDriveCommercial)
foreach ($e in $envPaths) {
    if ($e -and (Test-Path $e)) { $OneDrive = $e; break }
}

# Method 2: Registry
if (-not $OneDrive) {
    try {
        $regPath = (Get-ItemProperty "HKCU:\Software\Microsoft\OneDrive" -Name "UserFolder" -EA SilentlyContinue).UserFolder
        if ($regPath -and (Test-Path $regPath)) { $OneDrive = $regPath }
    } catch {}
}

# Method 3: Common paths
if (-not $OneDrive) {
    $tryPaths = @(
        "$env:USERPROFILE\OneDrive",
        "$env:USERPROFILE\OneDrive - Personal",
        "$env:USERPROFILE\OneDrive - Embodier",
        "C:\Users\Espen\OneDrive",
        "C:\Users\Espen\OneDrive - Personal"
    )
    foreach ($p in $tryPaths) {
        if (Test-Path $p) { $OneDrive = $p; break }
    }
}

# Method 4: Deep search — find any OneDrive folder under user profile
if (-not $OneDrive) {
    $found = Get-ChildItem "$env:USERPROFILE" -Directory -Filter "OneDrive*" -EA SilentlyContinue | Select-Object -First 1
    if ($found) { $OneDrive = $found.FullName }
}

if (-not $OneDrive) {
    Write-Host "ERROR: Cannot find OneDrive folder!" -ForegroundColor Red
    Write-Host "Please enter your OneDrive path:" -ForegroundColor Yellow
    $OneDrive = Read-Host "OneDrive path"
    if (-not (Test-Path $OneDrive)) {
        Write-Host "Path does not exist. Aborting." -ForegroundColor Red
        exit 1
    }
}

# Now check if Trading-Sync already exists, or if OneDrive has a nested structure
$SyncRoot = $null

# Direct check
if (Test-Path "$OneDrive\Trading-Sync") {
    $SyncRoot = "$OneDrive\Trading-Sync"
}

# Search one level deep (handles "Documents\New folder (2)\OneDrive" nesting)
if (-not $SyncRoot) {
    $nested = Get-ChildItem $OneDrive -Directory -Recurse -Depth 3 -Filter "Trading-Sync" -EA SilentlyContinue | Select-Object -First 1
    if ($nested) { $SyncRoot = $nested.FullName }
}

# Not found — create it at OneDrive root
if (-not $SyncRoot) {
    $SyncRoot = Join-Path $OneDrive "Trading-Sync"
}

Write-Host "[OK] OneDrive:    $OneDrive" -ForegroundColor Green
Write-Host "[OK] Sync root:   $SyncRoot" -ForegroundColor Green

# ═══════════════════════════════════════════════
# 2. FIND OR CREATE C:\Trading
# ═══════════════════════════════════════════════
$TradingDir = $null
foreach ($t in @("C:\Trading", "D:\Trading", "$env:USERPROFILE\Trading")) {
    if (Test-Path $t) { $TradingDir = $t; break }
}
if (-not $TradingDir) {
    $TradingDir = "C:\Trading"
    New-Item -ItemType Directory -Path $TradingDir -Force | Out-Null
    Write-Host "[NEW] Created $TradingDir" -ForegroundColor Yellow
}
Write-Host "[OK] Trading dir: $TradingDir" -ForegroundColor Green

# ═══════════════════════════════════════════════
# 3. FIND PYTHON
# ═══════════════════════════════════════════════
$Python = $null
foreach ($cmd in @("python", "python3", "py")) {
    $p = (Get-Command $cmd -EA SilentlyContinue).Source
    if ($p) { $Python = $p; break }
}
if (-not $Python) {
    $globs = @("$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe","C:\Python3*\python.exe")
    foreach ($g in $globs) {
        $f = Get-Item $g -EA SilentlyContinue | Select-Object -First 1
        if ($f) { $Python = $f.FullName; break }
    }
}
if (-not $Python) {
    Write-Host "ERROR: Python not found! Install Python 3.10+ and re-run." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python:      $Python" -ForegroundColor Green

# ═══════════════════════════════════════════════
# 4. CREATE ALL FOLDER STRUCTURES
# ═══════════════════════════════════════════════
$allDirs = @(
    "$SyncRoot\brain\journal","$SyncRoot\brain\research","$SyncRoot\brain\strategies",
    "$SyncRoot\brain\sessions","$SyncRoot\brain\app_dev","$SyncRoot\env-configs",
    "$SyncRoot\backtest-results","$SyncRoot\pine-scripts","$SyncRoot\logs",
    "$TradingDir\.brain\journal","$TradingDir\.brain\research","$TradingDir\.brain\strategies",
    "$TradingDir\.brain\sessions","$TradingDir\.brain\app_dev"
)
foreach ($d in $allDirs) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
Write-Host "[OK] Folders created" -ForegroundColor Green

# ═══════════════════════════════════════════════
# 5. CLONE REPO IF MISSING
# ═══════════════════════════════════════════════
$repoDir = "$TradingDir\elite-trading-system"
if (-not (Test-Path $repoDir)) {
    Write-Host "[...] Cloning elite-trading-system..." -ForegroundColor Yellow
    & git clone "https://github.com/Espenator/elite-trading-system.git" $repoDir 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "[OK] Repo cloned" -ForegroundColor Green }
    else { Write-Host "[WARN] Git clone failed — clone manually later" -ForegroundColor Yellow }
} else {
    Write-Host "[OK] Repo exists: $repoDir" -ForegroundColor Green
}

# ═══════════════════════════════════════════════
# 6. WRITE sync.py — EMBEDDED (the sync engine)
# ═══════════════════════════════════════════════
$syncPy = "$SyncRoot\sync.py"
$needsWrite = (-not (Test-Path $syncPy))

if ($needsWrite) {
    Write-Host "[...] Creating sync.py..." -ForegroundColor Yellow

$syncCode = @'
#!/usr/bin/env python3
"""Embodier Trading Sync Engine — OneDrive bridge between ESPENMAIN & Profit Trader."""
import os, sys, shutil, hashlib, json, logging, time
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR/"sync.log",encoding="utf-8"),logging.StreamHandler(sys.stdout)])
log = logging.getLogger("trading-sync")

HOSTNAME = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME","unknown")).upper()
ONEDRIVE_SYNC = Path(os.environ.get("TRADING_SYNC_PATH", str(Path(__file__).parent)))
LOCAL_TRADING = Path(os.environ.get("LOCAL_TRADING_PATH", r"C:\Trading"))
DAEMON_INTERVAL = int(os.environ.get("SYNC_INTERVAL","300"))

SYNC_FILES = {
    "brain/CONTEXT.md":".brain/CONTEXT.md","brain/CLAUDE_INSTRUCTIONS.md":".brain/CLAUDE_INSTRUCTIONS.md",
    "brain/brain_tools.py":".brain/brain_tools.py","brain/brain.db":".brain/brain.db",
    "env-configs/backend.env":"elite-trading-system/backend/.env",
}
SYNC_DIRS = {
    "brain/journal":".brain/journal","brain/research":".brain/research",
    "brain/strategies":".brain/strategies","brain/sessions":".brain/sessions",
    "brain/app_dev":".brain/app_dev","backtest-results":"backtest-results","pine-scripts":"pine-scripts",
}
IGNORE = {".sync-manifest.json","sync.py","logs","__pycache__",".pyc",".sync-lock"}
MANIFEST = ONEDRIVE_SYNC / ".sync-manifest.json"
LOCK = ONEDRIVE_SYNC / ".sync-lock"

def fhash(p):
    if not p.exists(): return ""
    h=hashlib.md5()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(8192),b""): h.update(c)
    return h.hexdigest()

def fmtime(p): return p.stat().st_mtime if p.exists() else 0.0

def load_manifest():
    if MANIFEST.exists():
        try:
            with open(MANIFEST) as f: return json.load(f)
        except: pass
    return {"last_sync":None,"last_sync_by":None,"file_hashes":{}}

def save_manifest(m):
    m["last_sync"]=datetime.now().isoformat(); m["last_sync_by"]=HOSTNAME
    with open(MANIFEST,"w") as f: json.dump(m,f,indent=2)

def _del_lock():
    try: LOCK.unlink(missing_ok=True)
    except:
        try: LOCK.write_text(json.dumps({"host":"EXPIRED","time":0}))
        except: pass

def acquire_lock(timeout=30):
    start=time.time()
    while LOCK.exists():
        try:
            d=json.loads(LOCK.read_text())
            if time.time()-d.get("time",0)>120: log.warning(f"Breaking stale lock from {d.get('host')}"); _del_lock(); break
        except: _del_lock(); break
        if time.time()-start>timeout: return False
        time.sleep(1)
    try: LOCK.write_text(json.dumps({"host":HOSTNAME,"time":time.time()}))
    except: pass
    return True

def release_lock(): _del_lock()

def safe_copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_suffix(dst.suffix+".tmp")
    shutil.copy2(str(src),str(tmp)); tmp.replace(dst)

def collect_pairs():
    pairs=[]
    for sr,lr in SYNC_FILES.items(): pairs.append((ONEDRIVE_SYNC/sr, LOCAL_TRADING/lr, sr))
    for sdr,ldr in SYNC_DIRS.items():
        sd,ld=ONEDRIVE_SYNC/sdr, LOCAL_TRADING/ldr; seen=set()
        if ld.exists():
            for f in ld.rglob("*"):
                if f.is_file() and not any(p in str(f) for p in IGNORE):
                    r=f.relative_to(ld); pairs.append((sd/r,f,f"{sdr}/{r}")); seen.add(str(r))
        if sd.exists():
            for f in sd.rglob("*"):
                if f.is_file() and not any(p in str(f) for p in IGNORE):
                    r=f.relative_to(sd)
                    if str(r) not in seen: pairs.append((f,ld/r,f"{sdr}/{r}"))
    return pairs

def smart_sync():
    m=load_manifest(); known=m.get("file_hashes",{}); new_h={}
    pushed=pulled=conflicts=skipped=0
    for sp,lp,label in collect_pairs():
        sh,lh=fhash(sp),fhash(lp); kn=known.get(label,"")
        if sh==lh: new_h[label]=sh or lh; skipped+=1; continue
        se,le=sp.exists(),lp.exists()
        if le and not se: safe_copy(lp,sp); new_h[label]=lh; pushed+=1; log.info(f"  -> PUSH (new) {label}"); continue
        if se and not le: safe_copy(sp,lp); new_h[label]=sh; pulled+=1; log.info(f"  <- PULL (new) {label}"); continue
        lc,sc=(lh!=kn),(sh!=kn)
        if lc and not sc: safe_copy(lp,sp); new_h[label]=lh; pushed+=1; log.info(f"  -> PUSH       {label}")
        elif sc and not lc: safe_copy(sp,lp); new_h[label]=sh; pulled+=1; log.info(f"  <- PULL       {label}")
        elif lc and sc:
            if fmtime(lp)>=fmtime(sp): safe_copy(lp,sp); new_h[label]=lh; log.warning(f"  CONFLICT -> PUSH {label}")
            else: safe_copy(sp,lp); new_h[label]=sh; log.warning(f"  CONFLICT <- PULL {label}")
            conflicts+=1
        else:
            if fmtime(lp)>=fmtime(sp): safe_copy(lp,sp); new_h[label]=lh; pushed+=1
            else: safe_copy(sp,lp); new_h[label]=sh; pulled+=1
    m["file_hashes"]=new_h; m["stats"]={"pushed":pushed,"pulled":pulled,"conflicts":conflicts,"skipped":skipped}
    save_manifest(m)
    if pushed+pulled>0 or conflicts>0: log.info(f"Sync: {pushed} pushed, {pulled} pulled, {conflicts} conflicts, {skipped} unchanged")
    else: log.info(f"In sync - {skipped} files unchanged")
    return pushed,pulled,conflicts

def push_all():
    c=0
    for sp,lp,l in collect_pairs():
        if lp.exists(): safe_copy(lp,sp); c+=1; log.info(f"  -> {l}")
    m=load_manifest(); m["file_hashes"]={l:fhash(lp) for sp,lp,l in collect_pairs() if lp.exists()}; save_manifest(m)
    log.info(f"Force-pushed {c} files from {HOSTNAME}")

def pull_all():
    c=0
    for sp,lp,l in collect_pairs():
        if sp.exists(): safe_copy(sp,lp); c+=1; log.info(f"  <- {l}")
    m=load_manifest(); m["file_hashes"]={l:fhash(sp) for sp,lp,l in collect_pairs() if sp.exists()}; save_manifest(m)
    log.info(f"Force-pulled {c} files to {HOSTNAME}")

def show_status():
    m=load_manifest()
    print(f"\n{'='*50}\n  TRADING SYNC STATUS\n{'='*50}")
    print(f"  PC: {HOSTNAME}\n  Local: {LOCAL_TRADING}\n  Sync: {ONEDRIVE_SYNC}")
    print(f"  Last sync: {m.get('last_sync','Never')} by {m.get('last_sync_by','N/A')}")
    pairs=collect_pairs(); diffs=[]
    for sp,lp,l in pairs:
        if fhash(sp)!=fhash(lp):
            if lp.exists() and not sp.exists(): s="LOCAL ONLY"
            elif sp.exists() and not lp.exists(): s="SYNC ONLY"
            elif fmtime(lp)>fmtime(sp): s="LOCAL NEWER"
            else: s="SYNC NEWER"
            diffs.append((l,s))
    if not diffs: print(f"  All {len(pairs)} files in sync!")
    else:
        print(f"  {len(diffs)} of {len(pairs)} files differ:")
        for l,s in diffs: print(f"    [{s:12}] {l}")

def daemon():
    log.info(f"SYNC DAEMON STARTED on {HOSTNAME} (every {DAEMON_INTERVAL}s)")
    while True:
        try:
            a=acquire_lock(10)
            if not a: log.warning("Proceeding without lock")
            try: smart_sync()
            finally:
                if a: release_lock()
        except Exception as e: log.error(f"Sync error: {e}",exc_info=True); release_lock()
        time.sleep(DAEMON_INTERVAL)

if __name__=="__main__":
    cmds={"push":push_all,"pull":pull_all,"auto":smart_sync,"status":show_status,"daemon":daemon}
    if len(sys.argv)<2 or sys.argv[1] not in cmds:
        print(f"Embodier Trading Sync  |  PC: {HOSTNAME}")
        for c in cmds: print(f"  python sync.py {c}")
        sys.exit(0)
    cmd=sys.argv[1]; fn=cmds[cmd]
    if cmd in ("push","pull","auto"):
        a=acquire_lock()
        if not a: log.warning("Proceeding without lock")
        try: fn()
        finally:
            if a: release_lock()
    else: fn()
'@
    Set-Content -Path $syncPy -Value $syncCode -Encoding UTF8
    Write-Host "[OK] sync.py created" -ForegroundColor Green
} else {
    Write-Host "[OK] sync.py exists (keeping current)" -ForegroundColor Green
}

# ═══════════════════════════════════════════════
# 7. INITIAL SYNC
# ═══════════════════════════════════════════════
Write-Host "`n[...] Running initial sync..." -ForegroundColor Yellow
$env:LOCAL_TRADING_PATH = $TradingDir
$env:TRADING_SYNC_PATH = $SyncRoot
& $Python $syncPy auto 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host "[OK] Initial sync done" -ForegroundColor Green

# ═══════════════════════════════════════════════
# 8. INSTALL SCHEDULED TASK (every 5 min)
# ═══════════════════════════════════════════════
Write-Host "`n[...] Installing scheduled task..." -ForegroundColor Yellow
$existing = Get-ScheduledTask -TaskName $TaskName -EA SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }

$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"set LOCAL_TRADING_PATH=$TradingDir&& set TRADING_SYNC_PATH=$SyncRoot&& `"$Python`" `"$syncPy`" auto`"" `
    -WorkingDirectory $SyncRoot

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes $Interval) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Embodier Trading auto-sync via OneDrive (every ${Interval}m)" `
    -RunLevel Limited | Out-Null

Start-ScheduledTask -TaskName $TaskName -EA SilentlyContinue

Write-Host "[OK] Task installed and running" -ForegroundColor Green

# ═══════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════
Write-Host "`n================================================" -ForegroundColor Green
Write-Host "  DONE! $env:COMPUTERNAME IS NOW SYNCING" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "  OneDrive sync: $SyncRoot"
Write-Host "  Local trading: $TradingDir"
Write-Host "  Schedule:      Every $Interval min"
Write-Host ""
Write-Host "  Commands:" -ForegroundColor Gray
Write-Host "    python `"$syncPy`" status   — see what's synced" -ForegroundColor Gray
Write-Host "    python `"$syncPy`" push     — force push to OneDrive" -ForegroundColor Gray
Write-Host "    python `"$syncPy`" pull     — force pull from OneDrive" -ForegroundColor Gray
Write-Host ""
Write-Host "  NOW RUN THE SAME COMMAND ON THE OTHER PC!" -ForegroundColor Cyan
Write-Host ""
