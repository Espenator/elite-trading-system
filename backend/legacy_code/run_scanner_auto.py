"""
run_scanner_auto.py - Streamlit Auto-Launcher with Error Handling
Automatically launches the Momentum Scanner Streamlit UI
"""
import subprocess
import sys
import os
import time
import socket
from pathlib import Path

def check_port(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port=8501, max_attempts=10):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not check_port(port):
            return port
    return None

def main():
    """Main launcher function."""
    print("=" * 50)
    print("   🚀 MOMENTUM SCANNER PRO 🚀   ")
    print("=" * 50)
    print("\nStarting application...\n")
    
    # Get the script directory
    script_dir = Path(__file__).parent.resolve()
    filter_panel_path = script_dir / "filter_panel.py"
    
    # Check if filter_panel.py exists
    if not filter_panel_path.exists():
        print(f"❌ Error: filter_panel.py not found at {filter_panel_path}")
        input("\nPress Enter to exit...")
        return 1
    
    # Find available port
    port = find_available_port()
    if not port:
        print("❌ Error: Could not find an available port")
        input("\nPress Enter to exit...")
        return 1
    
    print(f"✅ Using port: {port}\n")
    print("Waiting for server to start...\n")
    
    try:
        # Launch Streamlit
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(filter_panel_path),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false"
        ]
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait a bit for the server to start
        time.sleep(3)
        
        if process.poll() is None:
            print(f"✅ Scanner launched successfully!")
            print(f"📊 Browser should open automatically\n")
            print(f"🌐 Local URL: http://localhost:{port}")
            print(f"\n{'=' * 50}")
            print("Keep this window open while using the app")
            print("Press Ctrl+C to stop the scanner...")
            print("=" * 50)
            
            # Keep the process running and show output
            try:
                for line in process.stdout:
                    # Filter out verbose logs, show only important info
                    if any(keyword in line.lower() for keyword in ['error', 'warning', 'traceback', 'exception']):
                        print(line, end='')
                        
                process.wait()
            except KeyboardInterrupt:
                print("\n\n⚠️ Shutting down scanner...")
                process.terminate()
                process.wait(timeout=5)
                print("✅ Scanner stopped successfully")
        else:
            print("❌ Failed to start Streamlit server")
            print("\nError output:")
            for line in process.stdout:
                print(line, end='')
            return 1
            
    except FileNotFoundError:
        print("❌ Error: Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("\n✅ Streamlit installed. Please run the script again.")
        input("\nPress Enter to exit...")
        return 1
        
    except Exception as e:
        print(f"\n❌ Error launching scanner: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        input("\nPress Enter to exit...")
    sys.exit(exit_code)

