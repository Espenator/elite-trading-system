#!/usr/bin/env python3
"""
Trading System Auto-Sync — OneDrive Bridge
Bidirectional sync between ESPENMAIN and Profit Trader via OneDrive.

Usage:
    python sync.py push      # Push local changes TO OneDrive
    python sync.py pull      # Pull latest FROM OneDrive to local
    python sync.py status    # Show what's different
    python sync.py auto      # Smart bidirectional merge (used by scheduler)
    python sync.py daemon    # Run continuously every 5 minutes

The OneDrive folder auto-syncs between both PCs, so:
  ESPENMAIN push → OneDrive → Profit Trader pull (and vice versa)
"""

import os
import sys
import shutil
import hashlib
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# ===== LOGGING =====
LOG_DIR = Path(os.environ.get("TRADING_SYNC_LOG_DIR", ""))
if not LOG_DIR.name:
    # Default: log next to this script
    LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "sync.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("trading-sync")

# ===== CONFIGURATION =====
HOSTNAME = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "unknown")).upper()

# OneDrive sync folder (same path on both PCs via OneDrive)
ONEDRIVE_SYNC = Path(os.environ.get(
    "TRADING_SYNC_PATH",
    r"C:\Users\Espen\OneDrive\Trading-Sync"
))

# Local trading folder
LOCAL_TRADING = Path(os.environ.get("LOCAL_TRADING_PATH", r"C:\Trading"))

# Daemon interval in seconds
DAEMON_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "300"))  # 5 min default

# ===== SYNC MAP =====
# {OneDrive relative path: Local relative path (from LOCAL_TRADING)}
SYNC_FILES = {
    "brain/CONTEXT.md":              ".brain/CONTEXT.md",
    "brain/CLAUDE_INSTRUCTIONS.md":  ".brain/CLAUDE_INSTRUCTIONS.md",
    "brain/brain_tools.py":          ".brain/brain_tools.py",
    "brain/brain.db":                ".brain/brain.db",
    "env-configs/backend.env":       "elite-trading-system/backend/.env",
}

SYNC_DIRS = {
    "brain/journal":    ".brain/journal",
    "brain/research":   ".brain/research",
    "brain/strategies": ".brain/strategies",
    "brain/sessions":   ".brain/sessions",
    "brain/app_dev":    ".brain/app_dev",
    "backtest-results": "backtest-results",
    "pine-scripts":     "pine-scripts",
}

# Files to never sync (prevent loops)
IGNORE_PATTERNS = {".sync-manifest.json", "sync.py", "logs", "__pycache__", ".pyc"}

MANIFEST_FILE = ONEDRIVE_SYNC / ".sync-manifest.json"
LOCK_FILE = ONEDRIVE_SYNC / ".sync-lock"


# ===== UTILITIES =====

def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def file_mtime(path: Path) -> float:
    if not path.exists():
        return 0.0
    return path.stat().st_mtime


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("Corrupt manifest, starting fresh")
    return {"last_sync": None, "last_sync_by": None, "file_hashes": {}}


def save_manifest(manifest: dict):
    manifest["last_sync"] = datetime.now().isoformat()
    manifest["last_sync_by"] = HOSTNAME
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)


def acquire_lock(timeout: int = 30) -> bool:
    """Simple file-based lock to prevent two PCs syncing simultaneously."""
    start = time.time()
    while LOCK_FILE.exists():
        try:
            lock_data = json.loads(LOCK_FILE.read_text())
            lock_age = time.time() - lock_data.get("time", 0)
            if lock_age > 120:  # Stale lock (>2 min old)
                log.warning(f"Breaking stale lock from {lock_data.get('host')}")
                _delete_lock()
                break
        except Exception:
            _delete_lock()
            break

        if time.time() - start > timeout:
            log.error("Could not acquire sync lock — another sync in progress")
            return False
        time.sleep(1)

    try:
        LOCK_FILE.write_text(json.dumps({"host": HOSTNAME, "time": time.time()}))
    except OSError:
        pass  # If we can't write lock, proceed anyway (single-PC mode)
    return True


def _delete_lock():
    """Delete lock file, handling permission issues gracefully."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except (PermissionError, OSError):
        # Can't delete — overwrite with expired lock instead
        try:
            LOCK_FILE.write_text(json.dumps({"host": "EXPIRED", "time": 0}))
        except OSError:
            pass


def release_lock():
    _delete_lock()


def safe_copy(src: Path, dst: Path):
    """Copy file with parent dir creation and atomic write."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Copy to temp first, then rename (atomic on same filesystem)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(str(src), str(tmp))
    tmp.replace(dst)


# ===== CORE SYNC LOGIC =====

def collect_all_pairs():
    """Collect all (sync_path, local_path) file pairs."""
    pairs = []

    # Individual files
    for sync_rel, local_rel in SYNC_FILES.items():
        pairs.append((ONEDRIVE_SYNC / sync_rel, LOCAL_TRADING / local_rel, sync_rel))

    # Directory contents
    for sync_dir_rel, local_dir_rel in SYNC_DIRS.items():
        sync_dir = ONEDRIVE_SYNC / sync_dir_rel
        local_dir = LOCAL_TRADING / local_dir_rel

        seen = set()

        if local_dir.exists():
            for f in local_dir.rglob("*"):
                if f.is_file() and not any(p in str(f) for p in IGNORE_PATTERNS):
                    rel = f.relative_to(local_dir)
                    sync_file = sync_dir / rel
                    pairs.append((sync_file, f, f"{sync_dir_rel}/{rel}"))
                    seen.add(str(rel))

        if sync_dir.exists():
            for f in sync_dir.rglob("*"):
                if f.is_file() and not any(p in str(f) for p in IGNORE_PATTERNS):
                    rel = f.relative_to(sync_dir)
                    if str(rel) not in seen:
                        local_file = local_dir / rel
                        pairs.append((f, local_file, f"{sync_dir_rel}/{rel}"))

    return pairs


def smart_sync():
    """
    Bidirectional smart sync using last-known hashes.

    Logic per file:
    - If local changed but sync didn't → push local to sync
    - If sync changed but local didn't → pull sync to local
    - If both changed → newer wins (with conflict log)
    - If neither changed → skip
    - If file only exists on one side → copy to other
    """
    manifest = load_manifest()
    known_hashes = manifest.get("file_hashes", {})
    new_hashes = {}

    pushed = 0
    pulled = 0
    conflicts = 0
    skipped = 0

    pairs = collect_all_pairs()

    for sync_path, local_path, label in pairs:
        sync_hash = file_hash(sync_path)
        local_hash = file_hash(local_path)
        known = known_hashes.get(label, "")

        # Both identical
        if sync_hash == local_hash:
            new_hashes[label] = sync_hash or local_hash
            skipped += 1
            continue

        sync_exists = sync_path.exists()
        local_exists = local_path.exists()

        # Only exists on one side
        if local_exists and not sync_exists:
            safe_copy(local_path, sync_path)
            new_hashes[label] = local_hash
            pushed += 1
            log.info(f"  → PUSH (new)  {label}")
            continue

        if sync_exists and not local_exists:
            safe_copy(sync_path, local_path)
            new_hashes[label] = sync_hash
            pulled += 1
            log.info(f"  ← PULL (new)  {label}")
            continue

        # Both exist but different — check what changed since last sync
        local_changed = (local_hash != known)
        sync_changed = (sync_hash != known)

        if local_changed and not sync_changed:
            # Only local changed → push
            safe_copy(local_path, sync_path)
            new_hashes[label] = local_hash
            pushed += 1
            log.info(f"  → PUSH        {label}")

        elif sync_changed and not local_changed:
            # Only sync changed → pull
            safe_copy(sync_path, local_path)
            new_hashes[label] = sync_hash
            pulled += 1
            log.info(f"  ← PULL        {label}")

        elif local_changed and sync_changed:
            # CONFLICT: both changed — newer wins
            local_time = file_mtime(local_path)
            sync_time = file_mtime(sync_path)

            if local_time >= sync_time:
                safe_copy(local_path, sync_path)
                new_hashes[label] = local_hash
                log.warning(f"  ⚡ CONFLICT → PUSH (local newer)  {label}")
            else:
                safe_copy(sync_path, local_path)
                new_hashes[label] = sync_hash
                log.warning(f"  ⚡ CONFLICT ← PULL (sync newer)   {label}")
            conflicts += 1

        else:
            # Neither changed from known but they differ?
            # Edge case: use newest
            local_time = file_mtime(local_path)
            sync_time = file_mtime(sync_path)
            if local_time >= sync_time:
                safe_copy(local_path, sync_path)
                new_hashes[label] = local_hash
                pushed += 1
            else:
                safe_copy(sync_path, local_path)
                new_hashes[label] = sync_hash
                pulled += 1

    manifest["file_hashes"] = new_hashes
    manifest["last_auto_sync_by"] = HOSTNAME
    manifest["stats"] = {
        "pushed": pushed,
        "pulled": pulled,
        "conflicts": conflicts,
        "skipped": skipped,
        "total_files": len(pairs),
    }
    save_manifest(manifest)

    total_actions = pushed + pulled
    if total_actions > 0 or conflicts > 0:
        log.info(f"✅ Sync complete: {pushed} pushed, {pulled} pulled, {conflicts} conflicts, {skipped} unchanged")
    else:
        log.info(f"✅ In sync — {skipped} files unchanged")

    return pushed, pulled, conflicts


def push_all():
    """Force push all local files to OneDrive."""
    count = 0
    for sync_path, local_path, label in collect_all_pairs():
        if local_path.exists():
            safe_copy(local_path, sync_path)
            count += 1
            log.info(f"  → {label}")

    manifest = load_manifest()
    manifest["last_push_by"] = HOSTNAME
    # Update hashes
    manifest["file_hashes"] = {
        label: file_hash(local_path)
        for sync_path, local_path, label in collect_all_pairs()
        if local_path.exists()
    }
    save_manifest(manifest)
    log.info(f"✅ Force-pushed {count} files from {HOSTNAME}")


def pull_all():
    """Force pull all files from OneDrive to local."""
    count = 0
    for sync_path, local_path, label in collect_all_pairs():
        if sync_path.exists():
            safe_copy(sync_path, local_path)
            count += 1
            log.info(f"  ← {label}")

    manifest = load_manifest()
    manifest["last_pull_by"] = HOSTNAME
    manifest["file_hashes"] = {
        label: file_hash(sync_path)
        for sync_path, local_path, label in collect_all_pairs()
        if sync_path.exists()
    }
    save_manifest(manifest)
    log.info(f"✅ Force-pulled {count} files to {HOSTNAME}")


def show_status():
    """Display current sync status."""
    manifest = load_manifest()
    stats = manifest.get("stats", {})

    print(f"\n{'═' * 50}")
    print(f"  TRADING SYNC STATUS")
    print(f"{'═' * 50}")
    print(f"  This PC:        {HOSTNAME}")
    print(f"  Local:          {LOCAL_TRADING}")
    print(f"  OneDrive Sync:  {ONEDRIVE_SYNC}")
    print(f"  Last sync:      {manifest.get('last_sync', 'Never')}")
    print(f"  Last sync by:   {manifest.get('last_sync_by', 'N/A')}")
    if stats:
        print(f"  Last run:       {stats.get('pushed', 0)} pushed, {stats.get('pulled', 0)} pulled, {stats.get('conflicts', 0)} conflicts")
    print(f"{'─' * 50}")

    pairs = collect_all_pairs()
    diffs = []
    for sync_path, local_path, label in pairs:
        sh = file_hash(sync_path)
        lh = file_hash(local_path)
        if sh != lh:
            se = sync_path.exists()
            le = local_path.exists()
            if le and not se:
                status = "LOCAL ONLY"
            elif se and not le:
                status = "SYNC ONLY"
            elif file_mtime(local_path) > file_mtime(sync_path):
                status = "LOCAL NEWER"
            else:
                status = "SYNC NEWER"
            diffs.append((label, status))

    if not diffs:
        print(f"  ✅ All {len(pairs)} files in sync!")
    else:
        print(f"  ⚠️  {len(diffs)} of {len(pairs)} files differ:\n")
        for label, status in diffs:
            icon = {"LOCAL ONLY": "📤", "SYNC ONLY": "📥", "LOCAL NEWER": "→", "SYNC NEWER": "←"}.get(status, "?")
            print(f"    {icon} [{status:12}] {label}")

    print()


def daemon():
    """Run sync continuously every DAEMON_INTERVAL seconds."""
    log.info(f"{'═' * 50}")
    log.info(f"  TRADING SYNC DAEMON STARTED")
    log.info(f"  PC: {HOSTNAME}")
    log.info(f"  Interval: {DAEMON_INTERVAL}s ({DAEMON_INTERVAL // 60}m)")
    log.info(f"  Local: {LOCAL_TRADING}")
    log.info(f"  Sync:  {ONEDRIVE_SYNC}")
    log.info(f"{'═' * 50}")

    while True:
        try:
            if acquire_lock(timeout=10):
                try:
                    smart_sync()
                finally:
                    release_lock()
            else:
                log.warning("Skipping cycle — could not acquire lock")
        except Exception as e:
            log.error(f"Sync error: {e}", exc_info=True)
            release_lock()

        time.sleep(DAEMON_INTERVAL)


# ===== ENTRY POINT =====

COMMANDS = {
    "push":   ("Force push local → OneDrive", push_all),
    "pull":   ("Force pull OneDrive → local", pull_all),
    "auto":   ("Smart bidirectional sync", smart_sync),
    "status": ("Show sync status", show_status),
    "daemon": ("Run continuously", daemon),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Embodier Trading Sync — OneDrive Bridge")
        print(f"PC: {HOSTNAME}\n")
        print("Commands:")
        for cmd, (desc, _) in COMMANDS.items():
            print(f"  python sync.py {cmd:10} — {desc}")
        sys.exit(0)

    cmd = sys.argv[1]
    _, fn = COMMANDS[cmd]

    if cmd in ("push", "pull", "auto"):
        acquired = acquire_lock()
        if not acquired:
            log.warning("Proceeding without lock (single-machine mode)")
        try:
            fn()
        finally:
            if acquired:
                release_lock()
    else:
        fn()
