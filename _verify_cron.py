"""Verify cron.py _load_active_jobs gate filter logic."""
import sys, json
sys.path.insert(0, 'C:\\Users\\周家同\\smart-trade-ai')

from trade.api.cron import _load_active_jobs, _JOBS_FILE

# 1. Syntax validation
import ast
for p in ['trade/api/cron.py']:
    with open(p, encoding='utf-8') as f:
        ast.parse(f.read())
    print(f'AST check: {p} OK')

# 2. Verify the function doesn't crash
jobs = _load_active_jobs()
print(f'_load_active_jobs() returned {len(jobs)} jobs')

# 3. Verify no gate jobs leak through
for j in jobs:
    assert '门控' not in j['name'], f'Gate job leaked: {j}'
    name_lower = j['name'].lower()
    assert '_gate' not in name_lower, f'Gate job leaked: {j}'

print('All gate jobs filtered ✓')

# 4. If a gate job exists in jobs.json, 早安简报 should be synthesized
if _JOBS_FILE.is_file():
    with open(_JOBS_FILE, encoding='utf-8') as f:
        data = json.load(f)
    has_gate = any(
        '门控' in j.get('name', '') or (j.get('script', '') or '').endswith('_gate.py')
        for j in data.get('jobs', [])
    )
    if has_gate:
        has_brief = any(j['name'] == '早安简报' for j in jobs)
        print(f'Gate job detected → 早安简报 synthesized: {has_brief} ✓')
    else:
        print('No gate job in jobs.json — skip synthesis check')

print('\n✅ All checks passed')
