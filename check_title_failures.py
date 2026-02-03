#!/usr/bin/env python
"""Check title failures after whitespace normalization"""
import json
from pathlib import Path

json_file = Path('reports/db_solr_sync_failures.json')
if not json_file.exists():
    print("JSON file not found!")
    exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

failures = data.get('failures', [])
total_failures = data.get('total_failures', 0)

print("=" * 80)
print("FAILURE ANALYSIS AFTER TITLE WHITESPACE NORMALIZATION")
print("=" * 80)

title_failures = [f for f in failures if 'title:' in f.get('msg', '')]
work_mode_failures = [f for f in failures if 'Work Mode' in f.get('msg', '')]
other_failures = [f for f in failures if 'title:' not in f.get('msg', '') and 'Work Mode' not in f.get('msg', '')]

print(f"\nTotal Failures: {total_failures}")
print(f"  - Title Failures: {len(title_failures)}")
print(f"  - Work Mode Failures: {len(work_mode_failures)}")
print(f"  - Other Failures: {len(other_failures)}")

print(f"\nSample Title Failures (first 5):")
for i, f in enumerate(title_failures[:5], 1):
    print(f"  [{i}] Job {f.get('id')}: {f.get('msg', 'N/A')[:100]}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
