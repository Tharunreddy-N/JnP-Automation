#!/usr/bin/env python
"""Analyze all job failures from background test"""
import json
from pathlib import Path
from collections import Counter

json_file = Path('reports/db_solr_sync_failures.json')
if not json_file.exists():
    print("JSON file not found!")
    exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 80)
print("BACKGROUND TEST - ALL JOB FAILURES ANALYSIS")
print("=" * 80)

total_jobs = data.get('total_jobs_checked', 0)
total_failures = data.get('total_failures', 0)
failures = data.get('failures', [])

print(f"\nTotal Jobs Checked: {total_jobs:,}")
print(f"Total Failures: {total_failures:,}")
print(f"Success Rate: {((total_jobs - total_failures) / total_jobs * 100) if total_jobs > 0 else 0:.2f}%")

# Analyze failure types
print("\n" + "=" * 80)
print("FAILURE TYPES BREAKDOWN:")
print("=" * 80)

error_categories = Counter()
for failure in failures:
    msg = failure.get('msg', 'Unknown')
    # Extract error category (first part before ':')
    if ':' in msg:
        category = msg.split(':')[0].strip()
    else:
        category = msg[:50] if len(msg) > 50 else msg
    error_categories[category] += 1

print("\nTop 10 Failure Categories:")
for i, (category, count) in enumerate(error_categories.most_common(10), 1):
    percentage = (count / total_failures * 100) if total_failures > 0 else 0
    print(f"  {i:2d}. {category[:60]:<60} : {count:3d} ({percentage:5.2f}%)")

# Show sample failures for each category
print("\n" + "=" * 80)
print("SAMPLE FAILURES BY CATEGORY:")
print("=" * 80)

for category, count in error_categories.most_common(5):
    print(f"\n{category} ({count} failures):")
    sample_count = 0
    for failure in failures:
        msg = failure.get('msg', '')
        if category in msg or (':' not in msg and category == msg[:50]):
            print(f"  - Job ID {failure.get('id')}: {failure.get('db_title', 'N/A')[:60]}")
            print(f"    Error: {msg[:100]}")
            sample_count += 1
            if sample_count >= 3:  # Show max 3 samples per category
                break

print("\n" + "=" * 80)
print("Analysis Complete!")
print("=" * 80)
