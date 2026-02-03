#!/usr/bin/env python
"""Analyze title mismatches from db_solr_sync failures"""
import json
from pathlib import Path
import re

json_file = Path('reports/db_solr_sync_failures.json')
if not json_file.exists():
    print("JSON file not found!")
    exit(1)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

failures = data.get('failures', [])
title_failures = [f for f in failures if 'title:' in f.get('msg', '')]

print("=" * 100)
print("TITLE MISMATCH ANALYSIS")
print("=" * 100)
print(f"\nTotal Title Failures: {len(title_failures)} out of {len(failures)} total failures\n")

for i, failure in enumerate(title_failures, 1):
    job_id = failure.get('id', 'N/A')
    db_title = failure.get('db_title', 'N/A')
    msg = failure.get('msg', '')
    
    # Extract DB and Solr titles from error message
    db_match = re.search(r"DB='([^']+)'", msg)
    solr_match = re.search(r"Solr='([^']+)'", msg)
    
    db_title_from_msg = db_match.group(1) if db_match else db_title
    solr_title_from_msg = solr_match.group(1) if solr_match else 'N/A'
    
    print(f"\n[{i}] Job ID: {job_id}")
    print(f"    DB Title:   {db_title_from_msg}")
    print(f"    Solr Title: {solr_title_from_msg}")
    
    # Show character differences
    if 'Diff chars:' in msg:
        diff_match = re.search(r"Diff chars: \[([^\]]+)\]", msg)
        if diff_match:
            print(f"    Different Characters: {diff_match.group(1)}")
    
    # Show length if available
    if 'Length:' in msg:
        length_match = re.search(r"Length: DB=(\d+), Solr=(\d+)", msg)
        if length_match:
            print(f"    Length: DB={length_match.group(1)}, Solr={length_match.group(2)}")
    
    # Character-by-character comparison for first 100 chars
    if db_title_from_msg != 'N/A' and solr_title_from_msg != 'N/A':
        db_chars = list(db_title_from_msg[:100])
        solr_chars = list(solr_title_from_msg[:100])
        max_len = max(len(db_chars), len(solr_chars))
        
        differences = []
        for idx in range(max_len):
            db_char = db_chars[idx] if idx < len(db_chars) else None
            solr_char = solr_chars[idx] if idx < len(solr_chars) else None
            if db_char != solr_char:
                db_display = repr(db_char) if db_char else 'END'
                solr_display = repr(solr_char) if solr_char else 'END'
                differences.append(f"Pos {idx}: DB={db_display}, Solr={solr_display}")
                if len(differences) >= 5:  # Show first 5 differences
                    break
        
        if differences:
            print(f"    First Differences:")
            for diff in differences:
                print(f"      {diff}")

print("\n" + "=" * 100)
print("Analysis Complete!")
print("=" * 100)
