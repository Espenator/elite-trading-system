#!/usr/bin/env python
"""
Elite Trading System - Backend Startup Script (Root Entry Point)

This script starts the FastAPI backend server.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent  # Go up one level to get the actual project root
sys.path.insert(0, str(project_root))

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Elite Trading System Backend...")
    print("🔗 API will be available at: http://localhost:8000")
    print("📝 API docs will be at: http://localhost:8000/docs")
    print("")
    
    try:
        uvicorn.run(
            "backend.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down backend...")
    except Exception as e:
        print(f"\n❌ Error starting backend: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
