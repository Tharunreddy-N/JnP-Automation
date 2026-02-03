#!/usr/bin/env python
"""Check if Hybrid jobs are being handled correctly"""
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
print("HYBRID JOB VERIFICATION")
print("=" * 80)

# Count failures by type
hybrid_failures = [f for f in failures if 'Hybrid' in f.get('msg', '')]
remote_failures = [f for f in failures if 'Remote' in f.get('msg', '') and 'Hybrid' not in f.get('msg', '')]
not_remote_failures = [f for f in failures if 'Not Remote' in f.get('msg', '') and 'Hybrid' not in f.get('msg', '')]
title_failures = [f for f in failures if 'title:' in f.get('msg', '')]
other_failures = [f for f in failures if 'Hybrid' not in f.get('msg', '') and 'Remote' not in f.get('msg', '') and 'title:' not in f.get('msg', '')]

print(f"\nTotal Failures: {total_failures}")
print(f"  - Hybrid-related: {len(hybrid_failures)}")
print(f"  - Remote (not Hybrid): {len(remote_failures)}")
print(f"  - Not Remote: {len(not_remote_failures)}")
print(f"  - Title mismatches: {len(title_failures)}")
print(f"  - Other: {len(other_failures)}")

# Check if remote field is being used
remote_field_used = [f for f in failures if 'from Solr field: remote' in f.get('msg', '')]
workmode_field_used = [f for f in failures if 'from Solr field: workmode' in f.get('msg', '')]

print(f"\nSolr Field Usage:")
print(f"  - Using 'remote' field: {len(remote_field_used)}")
print(f"  - Using 'workmode' field: {len(workmode_field_used)}")

# Show sample Hybrid failures
print(f"\nSample Hybrid Failures (first 5):")
for i, f in enumerate(hybrid_failures[:5], 1):
    print(f"  [{i}] Job ID: {f.get('id')}")
    print(f"      Title: {f.get('db_title', 'N/A')[:60]}")
    print(f"      Error: {f.get('msg', 'N/A')[:80]}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
