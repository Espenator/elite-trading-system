# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Embodier Trader Backend.

Bundles the FastAPI/uvicorn backend into a single directory (--onedir).
Output: backend/dist/embodier-backend/embodier-backend.exe

Usage:
    cd backend
    pyinstaller ../desktop/embodier-backend.spec
"""

import os
import sys
from pathlib import Path

block_cipher = None

BACKEND_DIR = os.path.abspath(os.path.join(SPECPATH, '..', 'backend'))

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(BACKEND_DIR, 'run_server.py')],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=[
        # Include the app package
        (os.path.join(BACKEND_DIR, 'app'), 'app'),
        # Include .env if present (will be overwritten by Electron at runtime)
        (os.path.join(BACKEND_DIR, '.env'), '.') if os.path.exists(os.path.join(BACKEND_DIR, '.env')) else (None, None),
        # Include data directory templates
        (os.path.join(BACKEND_DIR, 'data'), 'data') if os.path.exists(os.path.join(BACKEND_DIR, 'data')) else (None, None),
    ],
    hiddenimports=[
        # FastAPI + uvicorn
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'pydantic',
        'pydantic_settings',
        'slowapi',
        # HTTP
        'httpx',
        'aiohttp',
        'websockets',
        # Data / ML
        'pandas',
        'numpy',
        'duckdb',
        'xgboost',
        'sklearn',
        'sklearn.ensemble',
        'sklearn.preprocessing',
        'sklearn.model_selection',
        'hmmlearn',
        'hmmlearn.hmm',
        # Trading
        'alpaca',
        'alpaca.trading',
        'alpaca.data',
        'alpaca.common',
        # Utilities
        'dotenv',
        'psutil',
        'cryptography',
        'apscheduler',
        'apscheduler.schedulers.asyncio',
        'apscheduler.triggers.cron',
        'apscheduler.triggers.interval',
        # gRPC
        'grpc',
        'grpc._cython',
        'grpc.aio',
        # Redis
        'redis',
        'redis.asyncio',
        # External APIs
        'youtube_transcript_api',
        # App modules (ensure all services are found)
        'app.main',
        'app.services',
        'app.api',
        'app.core',
        'app.modules',
        'app.council',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy packages not needed
        'torch',
        'tensorflow',
        'matplotlib',
        'tkinter',
        'PIL',
        'cv2',
        'scipy.spatial.cKDTree',  # Not needed, saves space
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out None entries from datas
a.datas = [(src, dst) for src, dst in a.datas if src is not None]

# ── PYZ Archive ──────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ──────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='embodier-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console app (logs to stdout)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, 'icons', 'icon.ico'),
)

# ── COLLECT (--onedir output) ────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='embodier-backend',
)
