#!/usr/bin/env python
"""
Elite Trading System - Backend Startup Script

This script ensures proper Python path setup before starting the FastAPI server.
Run this instead of 'uvicorn backend.main:app'
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print(f"✅ Project root added to path: {project_root}")
print(f"📁 Python path: {sys.path[0]}")

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Elite Trading System Backend...")
    print("🔗 API will be available at: http://localhost:8000")
    print("📝 API docs will be at: http://localhost:8000/docs")
    print("")
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
