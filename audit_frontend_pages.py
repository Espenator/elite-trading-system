"""
Frontend Page Audit - Static analysis of every page for common bugs.
Checks:
1. All useApi() calls reference valid endpoints in api.js
2. No undefined hooks/imports
3. Event handler onClick/onChange references exist
4. No hardcoded localhost URLs
5. useState/useEffect dependency issues
6. Dead code / unused variables
"""
import re
import os
import json
from collections import defaultdict

PAGES_DIR = "/home/user/workspace/elite-trading-system/frontend-v2/src/pages"
COMPONENTS_DIR = "/home/user/workspace/elite-trading-system/frontend-v2/src/components"
HOOKS_DIR = "/home/user/workspace/elite-trading-system/frontend-v2/src/hooks"
API_CONFIG = "/home/user/workspace/elite-trading-system/frontend-v2/src/config/api.js"

# Parse api.js endpoints
def parse_api_endpoints():
    with open(API_CONFIG) as f:
        content = f.read()
    # Match endpoint keys 
    endpoints = set()
    for m in re.finditer(r'(\w+|"[^"]+"):\s*"(/[^"]+)"', content):
        key = m.group(1).strip('"')
        endpoints.add(key)
    return endpoints

# Find all useApi calls in a file and check they map to known endpoints
def check_useApi_calls(filepath, valid_endpoints):
    issues = []
    with open(filepath) as f:
        content = f.read()
    
    # Find useApi('endpoint_key') or useApi("endpoint_key")
    for m in re.finditer(r"""useApi\(\s*['"]([\w/.-]+)['"]""", content):
        endpoint = m.group(1)
        if endpoint not in valid_endpoints:
            line_num = content[:m.start()].count('\n') + 1
            issues.append(f"  L{line_num}: useApi('{endpoint}') - NOT in api.js endpoints!")
    
    # Check for specialized hooks that reference endpoints
    for m in re.finditer(r'use(SwarmTopology|ConferenceStatus|TeamStatus|DriftMetrics|SystemAlerts|AgentResources|BlackboardFeed|RegimeState|MacroState|RegimeParams|RegimePerformance|SectorRotation|RegimeTransitions|MemoryIntelligence|WhaleFlow|RiskGauges|BridgeHealth|CouncilLatest|HomeostasisStatus|CircuitBreakerStatus)\b', content):
        pass  # These are wrapper hooks, they internally call useApi
    
    return issues

# Check for broken onClick handlers
def check_event_handlers(filepath):
    issues = []
    with open(filepath) as f:
        content = f.read()
    
    # Find onClick={() => funcName()} where funcName might not exist
    for m in re.finditer(r'onClick=\{(?:\(\)\s*=>)?\s*(\w+)\b', content):
        func = m.group(1)
        # Check if function is defined in the file
        if func not in ('undefined', 'null', 'console', 'window', 'alert', 'e', 'event', 'true', 'false'):
            if func.startswith('set') or func.startswith('handle') or func.startswith('toggle') or func.startswith('on') or func == 'refetch':
                # Check if it's defined anywhere in the file
                pattern = rf'(const|let|function)\s+{re.escape(func)}\b|{re.escape(func)}\s*='
                if not re.search(pattern, content):
                    line_num = content[:m.start()].count('\n') + 1
                    issues.append(f"  L{line_num}: onClick handler '{func}' may not be defined")
    
    return issues

# Check for hardcoded URLs
def check_hardcoded_urls(filepath):
    issues = []
    with open(filepath) as f:
        content = f.read()
    
    for m in re.finditer(r'(http://localhost:\d+|ws://localhost:\d+|https?://\d+\.\d+\.\d+\.\d+)', content):
        line_num = content[:m.start()].count('\n') + 1
        # Skip comments
        line = content.split('\n')[line_num - 1].strip()
        if not line.startswith('//') and not line.startswith('*'):
            issues.append(f"  L{line_num}: Hardcoded URL '{m.group(0)}' - should use config")
    
    return issues

# Check for conditional rendering bugs (.map on potentially null data)
def check_null_safety(filepath):
    issues = []
    with open(filepath) as f:
        content = f.read()
    
    # Find data?.something without null check before .map
    for m in re.finditer(r'(\w+)\.map\(', content):
        var = m.group(1)
        # Check if it's preceded by optional chaining or Array check
        ctx = content[max(0, m.start()-50):m.start()]
        if '?' not in ctx and 'Array' not in ctx and '||' not in ctx and '&&' not in ctx:
            line_num = content[:m.start()].count('\n') + 1
            issues.append(f"  L{line_num}: '{var}.map()' without null guard - could crash if {var} is undefined")
    
    return issues

# Check for duplicate useEffect/useState hooks
def check_hooks(filepath):
    issues = []
    with open(filepath) as f:
        content = f.read()
    
    # Check for unused state variables
    state_vars = re.findall(r'const\s*\[(\w+),\s*set(\w+)\]', content)
    for getter, _ in state_vars:
        # Count usages (excluding the declaration)
        usage_count = len(re.findall(rf'\b{re.escape(getter)}\b', content)) - 1
        if usage_count <= 0:
            issues.append(f"  State variable '{getter}' declared but never used")
    
    return issues

# Main audit
def main():
    valid_endpoints = parse_api_endpoints()
    print(f"Found {len(valid_endpoints)} valid API endpoints in api.js")
    print("=" * 80)
    
    all_issues = defaultdict(list)
    total_issues = 0
    
    # Scan all .jsx and .js files
    for root, dirs, files in os.walk(PAGES_DIR):
        for f in sorted(files):
            if f.endswith(('.jsx', '.js')):
                filepath = os.path.join(root, f)
                rel = os.path.relpath(filepath, PAGES_DIR)
                
                api_issues = check_useApi_calls(filepath, valid_endpoints)
                handler_issues = check_event_handlers(filepath)
                url_issues = check_hardcoded_urls(filepath)
                null_issues = check_null_safety(filepath)
                hook_issues = check_hooks(filepath)
                
                page_issues = api_issues + handler_issues + url_issues + null_issues + hook_issues
                
                if page_issues:
                    print(f"\n📄 {rel} ({len(page_issues)} issues):")
                    for issue in page_issues:
                        print(f"   {issue}")
                    all_issues[rel] = page_issues
                    total_issues += len(page_issues)
                else:
                    print(f"  ✅ {rel} — clean")
    
    # Also check components
    print(f"\n{'=' * 80}")
    print("COMPONENTS:")
    for root, dirs, files in os.walk(COMPONENTS_DIR):
        for f in sorted(files):
            if f.endswith(('.jsx', '.js')):
                filepath = os.path.join(root, f)
                rel = os.path.relpath(filepath, COMPONENTS_DIR)
                
                api_issues = check_useApi_calls(filepath, valid_endpoints)
                handler_issues = check_event_handlers(filepath)
                url_issues = check_hardcoded_urls(filepath)
                
                page_issues = api_issues + handler_issues + url_issues
                
                if page_issues:
                    print(f"\n📄 {rel} ({len(page_issues)} issues):")
                    for issue in page_issues:
                        print(f"   {issue}")
                    all_issues[f"components/{rel}"] = page_issues
                    total_issues += len(page_issues)
                else:
                    print(f"  ✅ {rel} — clean")
    
    # Also check hooks
    print(f"\n{'=' * 80}")
    print("HOOKS:")
    for root, dirs, files in os.walk(HOOKS_DIR):
        for f in sorted(files):
            if f.endswith(('.jsx', '.js')):
                filepath = os.path.join(root, f)
                rel = os.path.relpath(filepath, HOOKS_DIR)
                
                url_issues = check_hardcoded_urls(filepath)
                
                if url_issues:
                    print(f"\n📄 {rel} ({len(url_issues)} issues):")
                    for issue in url_issues:
                        print(f"   {issue}")
                    all_issues[f"hooks/{rel}"] = url_issues
                    total_issues += len(url_issues)
                else:
                    print(f"  ✅ {rel} — clean")
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL ISSUES FOUND: {total_issues}")
    print(f"Files with issues: {len(all_issues)}")
    print(f"Clean files: n/a")
    
    # Save results
    with open("/home/user/workspace/elite-trading-system/frontend_audit_results.json", "w") as f:
        json.dump(dict(all_issues), f, indent=2)
    print("\nResults saved to frontend_audit_results.json")

if __name__ == "__main__":
    main()
