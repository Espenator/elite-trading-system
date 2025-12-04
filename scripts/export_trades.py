"""
Export trades to CSV
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def export_trades():
    log_file = Path('data/logs/trades.log')
    
    if not log_file.exists():
        print("❌ No trades found")
        return
    
    df = pd.read_csv(log_file)
    
    output_file = Path('data/exports') / f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"✅ Exported {len(df)} trades to {output_file}")

if __name__ == "__main__":
    export_trades()
