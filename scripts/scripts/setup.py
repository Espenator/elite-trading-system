"""
Setup script - Initialize the system
"""

import os
import sys
from pathlib import Path

def setup():
    print("🚀 Elite Trading System - Setup")
    print("=" * 70)
    
    # Create directories
    dirs = [
        'data/cache/ohlcv',
        'data/logs',
        'data/models',
        'data/exports',
        'credentials'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path}")
    
    # Create .gitkeep files
    for dir_path in dirs:
        gitkeep = Path(dir_path) / '.gitkeep'
        gitkeep.touch()
    
    # Check .env
    if not Path('.env').exists():
        print("\n⚠️  .env file not found!")
        print("   Copy .env.example to .env and fill in your credentials")
    else:
        print("\n✅ .env file exists")
    
    print("\n" + "=" * 70)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Edit config.yaml (set your trading style)")
    print("2. Fill in .env (Telegram, Google Sheets)")
    print("3. Run: python run.py")

if __name__ == "__main__":
    setup()
