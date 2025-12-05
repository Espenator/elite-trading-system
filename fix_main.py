import sys 
from pathlib import Path 
 
# Read main.py 
with open('backend/main.py', 'r', encoding='utf-8') as f: 
    lines = f.readlines() 
 
# Add sys.path fix at the top after imports 
fixed_lines = [] 
sys_path_added = False 
 
for i, line in enumerate(lines): 
    if line.strip().startswith('from core') and not sys_path_added: 
        fixed_lines.append('import sysn') 
        fixed_lines.append('sys.path.insert(0, str(Path(__file__).parent.parent))n') 
        sys_path_added = True 
    fixed_lines.append(line) 
 
with open('backend/main.py', 'w', encoding='utf-8') as f: 
    f.writelines(fixed_lines) 
 
print('Fixed main.py imports!') 
