# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Embodier Trader Backend.
Bundles the entire FastAPI backend into a single directory distribution.

Usage:
  cd backend/
  pyinstaller embodier-backend.spec --noconfirm

Output: dist/embodier-backend/ (directory with binary + all deps)
"""
import sys
import os
from pathlib import Path

block_cipher = None

# Project root
backend_dir = os.path.dirname(os.path.abspath(SPEC))

# Collect all app source files
app_tree = Tree(
    os.path.join(backend_dir, "app"),
    prefix="app",
    excludes=["__pycache__", "*.pyc", ".pytest_cache"],
)

a = Analysis(
    [os.path.join(backend_dir, "run_server.py")],
    pathex=[backend_dir],
    binaries=[],
    datas=[
        # Include default data files
        (os.path.join(backend_dir, ".env.example"), "."),
        # Include ML model artifacts if they exist
        (os.path.join(backend_dir, "app", "modules", "ml_engine", "artifacts"), os.path.join("app", "modules", "ml_engine", "artifacts")),
    ],
    hiddenimports=[
        # FastAPI + Uvicorn
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "pydantic",
        "pydantic.deprecated.decorator",
        # Database
        "duckdb",
        "sqlite3",
        # ML
        "xgboost",
        "sklearn",
        "sklearn.utils._cython_blas",
        "sklearn.neighbors.typedefs",
        "sklearn.neighbors.quad_tree",
        "sklearn.tree",
        "sklearn.tree._utils",
        "numpy",
        "pandas",
        # HTTP
        "httpx",
        "httpx._transports",
        "requests",
        "websockets",
        # Utils
        "apscheduler",
        "apscheduler.schedulers.asyncio",
        "apscheduler.triggers.cron",
        "apscheduler.triggers.interval",
        "cryptography",
        "cryptography.fernet",
        "dotenv",
        "psutil",
        "yaml",
        "youtube_transcript_api",
        # App modules
        "app.main",
        "app.core",
        "app.api",
        "app.services",
        "app.modules",
        "app.data",
        "app.council",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
        "jupyter",
        "notebook",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Merge the app source tree
a.datas += app_tree

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="embodier-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # Auto-detect (x64 or arm64)
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="embodier-backend",
)
