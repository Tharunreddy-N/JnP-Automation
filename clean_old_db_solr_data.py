#!/usr/bin/env python
"""Clean old db_solr_sync entries - keep only latest"""
import json
from pathlib import Path

# Read history file
hist_file = Path('logs/history/jobseeker_history.json')
if not hist_file.exists():
    print("History file not found!")
    exit(1)

with open(hist_file, 'r', encoding='utf-8') as f:
    history = json.load(f)

test_key = 'test_t1_09_db_solr_sync_verification'

if test_key in history:
    entries = history[test_key]
    print(f"Before cleanup: {len(entries)} entries found")
    
    if len(entries) > 0:
        # Keep only the latest entry (first one after sorting by datetime/date)
        def sort_key(entry):
            dt = entry.get('datetime') or entry.get('date', '')
            return dt
        
        sorted_entries = sorted(entries, key=sort_key, reverse=True)
        latest_entry = sorted_entries[0]
        
        print(f"Latest entry: Date={latest_entry.get('date')}, Status={latest_entry.get('status')}, Total Jobs={latest_entry.get('total_jobs', 0)}")
        
        # Keep only latest entry
        history[test_key] = [latest_entry]
        
        # Save cleaned history
        with open(hist_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        print(f"After cleanup: {len(history[test_key])} entry (only latest kept)")
        print("Old data removed successfully!")
    else:
        print("No entries to clean")
else:
    print(f"Test key '{test_key}' not found in history")
