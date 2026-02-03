#!/usr/bin/env python
"""Carefully analyze all 1450 failures"""
import json
from pathlib import Path
from collections import defaultdict

json_file = Path('reports/db_solr_sync_failures.json')
if not json_file.exists():
    print("JSON file not found!")
    exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

failures = data.get('failures', [])
total_failures = data.get('total_failures', 0)

print("=" * 100)
print("DETAILED FAILURE ANALYSIS - 1450 JOBS")
print("=" * 100)

# Categorize failures
categories = defaultdict(list)

for f in failures:
    msg = f.get('msg', '')
    if 'Work Mode' in msg:
        if 'Hybrid' in msg:
            categories['Work Mode: Hybrid'].append(f)
        elif 'Remote' in msg and 'Not Remote' in msg:
            categories['Work Mode: Remote vs Not Remote'].append(f)
        elif 'Not Remote' in msg:
            categories['Work Mode: Not Remote'].append(f)
        elif 'Remote' in msg:
            categories['Work Mode: Remote'].append(f)
    elif 'title:' in msg:
        categories['Title Mismatch'].append(f)
    elif 'Job Link:' in msg:
        categories['Job Link Mismatch'].append(f)
    elif 'Cityname:' in msg or 'Statename:' in msg:
        categories['Location Mismatch'].append(f)
    elif 'company_name:' in msg:
        categories['Company Name Mismatch'].append(f)
    elif 'ai_skills:' in msg:
        categories['AI Skills Mismatch'].append(f)
    else:
        categories['Other'].append(f)

print(f"\nTotal Failures: {total_failures}")
print(f"\nFailure Categories:")
for cat, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"  {cat:<40}: {len(items):>5} ({len(items)/total_failures*100:>5.1f}%)")

# Detailed analysis of Work Mode failures
print(f"\n" + "=" * 100)
print("WORK MODE FAILURES - DETAILED BREAKDOWN")
print("=" * 100)

work_mode_failures = [f for f in failures if 'Work Mode' in f.get('msg', '')]
print(f"\nTotal Work Mode Failures: {len(work_mode_failures)}")

# Check which Solr field was used
remote_field_count = len([f for f in work_mode_failures if 'from Solr field: remote' in f.get('msg', '')])
workmode_field_count = len([f for f in work_mode_failures if 'from Solr field: workmode' in f.get('msg', '')])

print(f"  - Using 'remote' field: {remote_field_count}")
print(f"  - Using 'workmode' field: {workmode_field_count}")

# Breakdown by DB value
db_not_remote = [f for f in work_mode_failures if 'DB=Not Remote' in f.get('msg', '')]
db_remote = [f for f in work_mode_failures if 'DB=Remote' in f.get('msg', '') and 'DB=Not Remote' not in f.get('msg', '')]
db_hybrid = [f for f in work_mode_failures if 'DB=Hybrid' in f.get('msg', '')]

print(f"\nBy DB Value:")
print(f"  - DB=Not Remote: {len(db_not_remote)}")
print(f"  - DB=Remote: {len(db_remote)}")
print(f"  - DB=Hybrid: {len(db_hybrid)}")

# Show samples
print(f"\nSample Failures - DB=Not Remote, Solr=Remote:")
for i, f in enumerate(db_not_remote[:3], 1):
    print(f"  [{i}] Job {f.get('id')}: {f.get('db_title', 'N/A')[:60]}")
    print(f"      Error: {f.get('msg', 'N/A')}")

print(f"\nSample Failures - DB=Hybrid, Solr=Not Remote:")
for i, f in enumerate(db_hybrid[:3], 1):
    print(f"  [{i}] Job {f.get('id')}: {f.get('db_title', 'N/A')[:60]}")
    print(f"      Error: {f.get('msg', 'N/A')}")

print("\n" + "=" * 100)
