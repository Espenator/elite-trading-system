import re 
import os 
 
# Fix scheduler.py 
scheduler_path = "backend/scheduler.py" 
with open(scheduler_path, 'r', encoding='utf-8') as f: 
    content = f.read() 
 
# Fix the imports 
content = content.replace('from core.logger import', 'from ..core.logger import') 
content = content.replace('from core.event_bus import', 'from ..core.event_bus import') 
 
with open(scheduler_path, 'w', encoding='utf-8') as f: 
    f.write(content) 
 
print("Fixed scheduler.py imports!") 
 
# Fix main.py 
main_path = "backend/main.py" 
with open(main_path, 'r', encoding='utf-8') as f: 
    content = f.read() 
 
content = content.replace('from backend.scheduler import ScannerManager', 'from backend.scheduler import TradingScheduler') 
 
with open(main_path, 'w', encoding='utf-8') as f: 
    f.write(content) 
 
print("Fixed main.py imports!") 
