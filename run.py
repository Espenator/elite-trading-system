"""
Elite Trading System - Master Launcher
Starts all components with one command: python run.py
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def check_dependencies():
    """Check if all required packages are installed"""
    print("🔍 Checking dependencies...")
    try:
        import fastapi
        import streamlit
        import gspread
        import yfinance
        print("✅ All core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n📦 Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed")
        return True

def start_backend():
    """Start FastAPI backend server"""
    print("\n🚀 Starting backend server...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return backend_process

def start_frontend():
    """Start Streamlit dashboard"""
    print("🎨 Starting dashboard...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return frontend_process

def start_ml_engine():
    """Start ML continuous learning engine"""
    print("🤖 Starting ML engine...")
    ml_process = subprocess.Popen(
        [sys.executable, "learning/continuous_learner.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return ml_process

def main():
    """Main launcher"""
    print("=" * 70)
    print("🚀 ELITE TRADING SYSTEM - LAUNCHER")
    print("=" * 70)
    print(f"📍 Location: {Path.cwd()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("=" * 70)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Failed to install dependencies. Exiting.")
        sys.exit(1)
    
    # Start components
    processes = []
    
    try:
        # Backend
        backend = start_backend()
        processes.append(("Backend", backend))
        time.sleep(3)  # Give backend time to start
        
        # Frontend
        frontend = start_frontend()
        processes.append(("Frontend", frontend))
        time.sleep(5)  # Give Streamlit time to start
        
        # ML Engine (optional - can be started separately)
        # ml = start_ml_engine()
        # processes.append(("ML Engine", ml))
        
        print("\n" + "=" * 70)
        print("✅ ALL SYSTEMS ONLINE")
        print("=" * 70)
        print("📊 Dashboard: http://localhost:8501")
        print("🔌 API:       http://localhost:8000")
        print("📖 API Docs:  http://localhost:8000/docs")
        print("=" * 70)
        print("\n🌐 Opening dashboard in browser...")
        time.sleep(2)
        webbrowser.open("http://localhost:8501")
        
        print("\n⚠️  Press Ctrl+C to stop all services\n")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        for name, process in processes:
            print(f"   Stopping {name}...")
            process.terminate()
        print("✅ All services stopped")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        for name, process in processes:
            process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
