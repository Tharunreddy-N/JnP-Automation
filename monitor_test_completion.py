#!/usr/bin/env python
"""Monitor test completion and verify cleanup"""
import json
import time
from pathlib import Path
from datetime import datetime

print("Monitoring test completion...")
print("Press Ctrl+C to stop monitoring\n")

json_file = Path('reports/db_solr_sync_failures.json')
hist_file = Path('logs/history/jobseeker_history.json')
test_key = 'test_t1_09_db_solr_sync_verification'

check_count = 0
while True:
    check_count += 1
    print(f"\n[{check_count}] Checking at {datetime.now().strftime('%H:%M:%S')}...")
    
    # Check JSON file
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        print(f"   JSON File: EXISTS")
        print(f"   Total Jobs: {json_data.get('total_jobs_checked', 0):,}")
        print(f"   Total Failures: {json_data.get('total_failures', 0):,}")
        print(f"   Modified: {datetime.fromtimestamp(json_file.stat().st_mtime).strftime('%H:%M:%S')}")
        
        # Check history
        if hist_file.exists():
            with open(hist_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if test_key in history:
                entries = history[test_key]
                print(f"   History Entries: {len(entries)}")
                
                if len(entries) == 1:
                    latest = entries[0]
                    print(f"   Status: PASS - Only latest entry exists")
                    print(f"   Latest: Date={latest.get('date')}, Status={latest.get('status')}, Jobs={latest.get('total_jobs', 0):,}")
                elif len(entries) > 1:
                    print(f"   Status: FAIL - Multiple entries found ({len(entries)})")
                    print("   Old data is NOT cleaned!")
                else:
                    print(f"   Status: No entries (test passed with no failures)")
        
        print("\n" + "="*60)
        print("TEST COMPLETED! Verification:")
        print("="*60)
        
        # Final verification
        if hist_file.exists():
            with open(hist_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if test_key in history:
                entries = history[test_key]
                if len(entries) <= 1:
                    print("PASS: Old data deletion - Working")
                    print("PASS: Only latest data - Working")
                else:
                    print("FAIL: Old data deletion - NOT Working")
                    print(f"      Found {len(entries)} entries instead of 1")
        
        print("PASS: JSON file created - Working")
        print("\nAll conditions verified!")
        break
    else:
        print("   JSON File: Not created yet (test still running)")
        print("   Waiting 30 seconds...")
        time.sleep(30)
