#!/usr/bin/env python
"""Check test status"""
import json
from pathlib import Path
from datetime import datetime

json_file = Path('reports/db_solr_sync_failures.json')
if json_file.exists():
    data = json.loads(json_file.read_text(encoding='utf-8'))
    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
    print(f"JSON File Status:")
    print(f"  Last Modified: {mtime}")
    print(f"  Total Jobs Checked: {data.get('total_jobs_checked', 0):,}")
    print(f"  Total Failures: {data.get('total_failures', 0):,}")
    print(f"  Failures List Length: {len(data.get('failures', []))}")
else:
    print("JSON file not found - test may still be running...")
