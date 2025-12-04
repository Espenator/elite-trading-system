"""
Backup configuration
"""

import shutil
from pathlib import Path
from datetime import datetime

def backup_config():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    files_to_backup = [
        'config.yaml',
        '.env'
    ]
    
    backup_dir = Path('data/backups')
    backup_dir.mkdir(exist_ok=True)
    
    for file in files_to_backup:
        if Path(file).exists():
            backup_path = backup_dir / f"{file}.{timestamp}.bak"
            shutil.copy(file, backup_path)
            print(f"✅ Backed up: {backup_path}")

if __name__ == "__main__":
    backup_config()
