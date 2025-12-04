"""
Clean cached data
"""

import shutil
from pathlib import Path

def clean_cache():
    print("🧹 Cleaning cache...")
    
    cache_dirs = [
        'data/cache/ohlcv',
        'data/logs',
        'data/exports'
    ]
    
    for dir_path in cache_dirs:
        path = Path(dir_path)
        if path.exists():
            for file in path.glob('*'):
                if file.is_file() and file.name != '.gitkeep':
                    file.unlink()
                    print(f"   Deleted: {file}")
    
    print("✅ Cache cleaned")

if __name__ == "__main__":
    clean_cache()
