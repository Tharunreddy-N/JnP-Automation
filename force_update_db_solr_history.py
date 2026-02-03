#!/usr/bin/env python
"""Force update db_solr_sync test history from JSON file"""
import json
from pathlib import Path
from datetime import datetime, timedelta

# Read JSON failure file
json_file = Path('reports/db_solr_sync_failures.json')
if not json_file.exists():
    print("JSON file not found!")
    exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    failures_data = json.load(f)

# Read history file
hist_file = Path('logs/history/jobseeker_history.json')
history = {}
if hist_file.exists():
    with open(hist_file, 'r', encoding='utf-8') as f:
        history = json.load(f)

# Get file modification time
file_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
test_date = file_mtime.strftime('%Y-%m-%d')

# Extract data from JSON
total_jobs = failures_data.get('total_jobs_checked', failures_data.get('total_jobs_available', 0))
error_count = failures_data.get('total_failures', 0)
failures_list = failures_data.get('failures', [])

print(f"JSON file data:")
print(f"  Total Jobs: {total_jobs}")
print(f"  Total Failures: {error_count}")
print(f"  File modified: {file_mtime}")
print(f"  Test date: {test_date}")

# Create test entry
test_name = 'test_t1_09_db_solr_sync_verification'

# Build failure message
structured_msg = "=" * 120 + "\n"
structured_msg += "SOLR SYNC FAILURE SUMMARY\n"
structured_msg += "=" * 120 + "\n"
if total_jobs > 0:
    structured_msg += f"Total Jobs Available in DB (last 24h): {total_jobs}\n"
structured_msg += f"Jobs Actually Checked: {total_jobs}\n"
structured_msg += f"Total Failures: {error_count}\n"
if error_count > 0 and total_jobs > 0:
    success_rate = ((total_jobs - error_count) / total_jobs * 100) if total_jobs > 0 else 0
    structured_msg += f"Success Rate: {success_rate:.2f}%\n"
structured_msg += "=" * 120 + "\n"
structured_msg += f"\n📄 Complete failure details saved in: reports/db_solr_sync_failures.json\n"

# Create new entry
new_entry = {
    'test_name': test_name,
    'status': 'FAIL' if error_count > 0 else 'PASS',
    'date': test_date,
    'datetime': file_mtime.isoformat(),
    'start_time': file_mtime.strftime('%Y%m%d %H:%M:%S'),
    'end_time': '',
    'running_time': 'N/A',
    'line_no': 0,
    'total_jobs': total_jobs,
    'error_jobs_count': error_count,
    'error_jobs': [{'id': str(f.get('id', 'N/A')), 'title': str(f.get('db_title', 'N/A'))[:100], 'error': str(f.get('msg', 'N/A'))[:500]} for f in failures_list[:error_count]],
    'failure_message': structured_msg[:2000] if error_count > 0 else '',
    'error_details': structured_msg[:2000] if error_count > 0 else ''
}

# Update history - replace same-day entry or add new
if test_name not in history:
    history[test_name] = []

# Remove any existing entry for today
history[test_name] = [e for e in history[test_name] if e.get('date') != test_date]

# Add new entry at the beginning (most recent first)
history[test_name].insert(0, new_entry)

# Keep only last 7 days
cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
history[test_name] = [e for e in history[test_name] if e.get('date', '') >= cutoff_date]

# Save history
with open(hist_file, 'w', encoding='utf-8') as f:
    json.dump(history, f, indent=2, ensure_ascii=False)

print(f"\nHistory updated successfully!")
print(f"  Status: {new_entry['status']}")
print(f"  Total Jobs: {new_entry['total_jobs']}")
print(f"  Failures: {new_entry['error_jobs_count']}")
print(f"  Date: {new_entry['date']}")
