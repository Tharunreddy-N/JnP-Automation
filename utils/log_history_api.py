"""
Log History API - Backend for 7-day log data viewer
Parses log files and provides API endpoints for historical test data
"""
import os
import re
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from flask import Flask, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Module configurations - Each module has separate data storage
MODULES = {
    'benchsale_admin': {
        'name': 'BenchSale Admin',
        'log_file': 'logs/benchsale_admin.log',
        'test_files': [
            'tests/benchsale/test_benchsale_admin_test_cases.py'
        ]
    },
    'benchsale_recruiter': {
        'name': 'BenchSale Recruiter',
        'log_file': 'logs/benchsale_recruiter.log',
        'test_files': [
            'tests/benchsale/test_benchsale_recruiter_test_cases.py'
        ]
    },
    'benchsale_test': {
        'name': 'BenchSale Main Test',
        'log_file': 'logs/benchsale_test.log',
        'test_files': [
            'tests/benchsale/test_benchsale_admin_test_cases.py',
            'tests/benchsale/test_benchsale_recruiter_test_cases.py'
        ]
    },
    'employer': {
        'name': 'Employer',
        'log_file': 'logs/employer.log',
        'test_files': ['tests/employer/test_employer_test_cases.py']
    },
    'jobseeker': {
        'name': 'JobSeeker',
        'log_file': 'logs/jobseeker.log',
        'test_files': [
            'tests/jobseeker/test_jobseeker_test_cases.py',
            'tests/jobseeker/test_t1_09_db_solr_sync.py'
        ]
    }
}

# Cache of allowed test names per module (from test files)
_ALLOWED_TESTS_CACHE: Dict[str, set] = {}

# Historical data storage directory (always relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = PROJECT_ROOT / 'logs' / 'history'
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

# Prevent concurrent heavy updates per module
_UPDATE_LOCKS: Dict[str, threading.Lock] = {}


def _start_update_if_needed(module_id: str):
    """Start background update only if log file is newer than history and no update is running."""
    if module_id not in MODULES:
        return

    project_root = get_project_root()
    log_file = project_root / MODULES[module_id]['log_file']
    history_file = HISTORY_DIR / f"{module_id}_history.json"

    if not log_file.exists():
        return

    # Skip update if history is already newer or equal to log file
    if history_file.exists():
        try:
            if history_file.stat().st_mtime >= log_file.stat().st_mtime:
                return
        except Exception:
            pass

    lock = _UPDATE_LOCKS.setdefault(module_id, threading.Lock())
    if not lock.acquire(blocking=False):
        return

    def _run():
        try:
            update_historical_data(module_id)
        except Exception as e:
            print(f"Background update error for {module_id}: {e}")
        finally:
            lock.release()

    threading.Thread(target=_run, daemon=True).start()


def get_project_root():
    """Get the project root directory"""
    return PROJECT_ROOT


def _dedupe_error_jobs(error_jobs: List[Dict]) -> List[Dict]:
    """De-duplicate error job entries using a stable key."""
    seen = set()
    deduped = []
    for item in error_jobs:
        job_id = str(item.get('id', '')).strip()
        title = str(item.get('title', '')).strip()
        error = str(item.get('error', '')).strip()
        key = (job_id, title, error)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def get_allowed_tests(module: str) -> set:
    """Get allowed test names for a module from its test files (strict allowlist)."""
    if module not in MODULES:
        return set()
    if module in _ALLOWED_TESTS_CACHE:
        return _ALLOWED_TESTS_CACHE[module]
    allowed: set = set()
    project_root = get_project_root()
    for test_file in MODULES[module].get('test_files', []):
        test_file_path = project_root / test_file
        if not test_file_path.exists():
            continue
        try:
            content = test_file_path.read_text(encoding='utf-8')
            matches = re.findall(r'def\s+(test_[a-zA-Z0-9_]+)', content, re.IGNORECASE)
            allowed.update(matches)
        except Exception as e:
            print(f"Error reading test file {test_file_path}: {e}")
    _ALLOWED_TESTS_CACHE[module] = allowed
    return allowed


def parse_test_from_log_line(line: str, line_no: int, log_date: datetime) -> Optional[Dict]:
    """Parse a single test result from a log line"""
    # Match patterns like: "TEST test_name: PASS" or "TEST test_name: FAIL"
    test_pattern = re.compile(r'TEST\s+([^:]+):\s*(PASS|FAIL|SKIP)', re.IGNORECASE)
    match = test_pattern.search(line)
    
    if not match:
        return None
    
    test_name = match.group(1).strip()
    status = match.group(2).upper()
    
    # Extract runtime if available
    elapsed_pattern = re.compile(
        r"Start\s*/\s*End\s*/\s*Elapsed:\s*[^/]+/\s*[^/]+/\s*([0-9:.]+)",
        re.IGNORECASE
    )
    runtime_seconds_pattern = re.compile(r"Runtime for .*?:\s*([0-9.]+)\s+seconds", re.IGNORECASE)
    
    running_time = 'N/A'
    elapsed_match = elapsed_pattern.search(line)
    if elapsed_match:
        running_time = elapsed_match.group(1).strip()
    else:
        runtime_match = runtime_seconds_pattern.search(line)
        if runtime_match:
            running_time = f"{runtime_match.group(1).strip()} seconds"
    
    return {
        'test_name': test_name,
        'status': status,
        'date': log_date.strftime('%Y-%m-%d'),
        'datetime': log_date.isoformat(),
        'running_time': running_time,
        'line_no': line_no
    }


def extract_date_from_log(lines: List[str]) -> Optional[datetime]:
    """Extract date from log file by looking for Start: timestamp"""
    # Pattern: "Start: 20260119 11:16:24.729" or "Start: 2026-01-19 11:16:24"
    date_pattern1 = re.compile(r'Start:\s*(\d{8})\s+(\d{2}):(\d{2}):(\d{2})', re.IGNORECASE)
    date_pattern2 = re.compile(r'Start:\s*(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})', re.IGNORECASE)
    
    for line in lines[:100]:  # Check first 100 lines
        match1 = date_pattern1.search(line)
        if match1:
            try:
                date_str = match1.group(1)
                hour = int(match1.group(2))
                minute = int(match1.group(3))
                second = int(match1.group(4))
                # Format: YYYYMMDD
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return datetime(year, month, day, hour, minute, second)
            except:
                pass
        
        match2 = date_pattern2.search(line)
        if match2:
            try:
                year = int(match2.group(1))
                month = int(match2.group(2))
                day = int(match2.group(3))
                hour = int(match2.group(4))
                minute = int(match2.group(5))
                second = int(match2.group(6))
                return datetime(year, month, day, hour, minute, second)
            except:
                pass
    
    return None


def parse_log_file(log_file_path: Path, log_date: datetime = None) -> List[Dict]:
    """Parse a log file and extract all test results with complete information"""
    tests = []
    
    if not log_file_path.exists():
        return tests
    
    try:
        # CRITICAL: Read entire log file to collect ALL past days' data
        # For very large log files, we still need to read more to get 7 days of history
        # Increase tail size to ensure we capture at least 7 days of data
        file_size = log_file_path.stat().st_size
        if file_size > 100 * 1024 * 1024:  # > 100MB
            # Read larger tail (50MB) to ensure we capture 7 days of history
            tail_size = 50 * 1024 * 1024  # 50MB tail
            with open(log_file_path, 'rb') as f:
                f.seek(max(0, file_size - tail_size), os.SEEK_SET)
                raw = f.read()
            lines = raw.decode('utf-8', errors='ignore').splitlines()
            print(f"Reading tail of large log file ({tail_size / (1024*1024):.1f}MB) to capture 7-day history")
        else:
            # For smaller files, read entire file to get all historical data
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            print(f"Reading entire log file ({file_size / (1024*1024):.1f}MB) to capture all historical data")
        
        # Try to extract date from log file, fallback to file modification time
        extracted_date = extract_date_from_log(lines)
        if extracted_date:
            log_date = extracted_date
        elif log_date is None:
            log_date = datetime.fromtimestamp(log_file_path.stat().st_mtime)
            
        # Match patterns like: "TEST test_name: PASS" or "TEST test_name: FAIL"
        test_pattern = re.compile(r'TEST\s+([^:]+):\s*(PASS|FAIL|SKIP)', re.IGNORECASE)
        elapsed_pattern = re.compile(
            r"Start\s*/\s*End\s*/\s*Elapsed:\s*([^/]+)\s*/\s*([^/]+)\s*/\s*([0-9:.]+)",
            re.IGNORECASE
        )
        runtime_seconds_pattern = re.compile(r"Runtime for .*?:\s*([0-9.]+)\s+seconds", re.IGNORECASE)
        start_time_pattern = re.compile(r'Start:\s*(\d{8})\s+(\d{2}):(\d{2}):(\d{2})', re.IGNORECASE)
        
        for line_no, line in enumerate(lines, 1):
            # Yield GIL every 1000 lines to keep server responsive during heavy parsing
            if line_no % 1000 == 0:
                time.sleep(0.001)
                
            match = test_pattern.search(line)
            if match:
                test_name = match.group(1).strip()
                status = match.group(2).upper()
                
                # Try to extract test-specific date from "Start:" line before this test
                test_date = log_date
                start_time_str = None
                end_time_str = None
                
                for back in range(max(0, line_no - 30), line_no):
                    if back < len(lines):
                        prev_line = lines[back]
                        date_match = start_time_pattern.search(prev_line)
                        if date_match:
                            try:
                                date_str = date_match.group(1)
                                hour = int(date_match.group(2))
                                minute = int(date_match.group(3))
                                second = int(date_match.group(4))
                                year = int(date_str[:4])
                                month = int(date_str[4:6])
                                day = int(date_str[6:8])
                                test_date = datetime(year, month, day, hour, minute, second)
                                start_time_str = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"
                                break
                            except:
                                pass
                
                # Look ahead for runtime information and failure details (within next 150 lines)
                running_time = 'N/A'
                failure_message = ''
                error_details = ''
                end_time = None
                total_jobs = 0
                error_jobs_count = 0
                error_jobs = []
                screenshot_path = None  # Extract screenshot path from logs
                
                # For db_solr_sync test, search entire log file for tabular format (it's logged much later)
                search_range = len(lines) if 'db_solr_sync' in test_name.lower() else min(line_no + 150, len(lines))
                
                for i in range(line_no, search_range):
                    if i < len(lines):
                        next_line = lines[i].strip()
                        # Stop if another test starts (but continue for db_solr_sync to find tabular format)
                        if i != line_no and test_pattern.search(next_line) and 'db_solr_sync' not in test_name.lower():
                            break
                        
                        # Check for elapsed time with start/end times
                        elapsed_match = elapsed_pattern.search(next_line)
                        if elapsed_match:
                            start_time_str = elapsed_match.group(1).strip()
                            end_time_str = elapsed_match.group(2).strip()
                            running_time = elapsed_match.group(3).strip()
                            # Try to parse end time
                            try:
                                end_match = re.search(r'(\d{8})\s+(\d{2}):(\d{2}):(\d{2})', end_time_str)
                                if end_match:
                                    date_str = end_match.group(1)
                                    hour = int(end_match.group(2))
                                    minute = int(end_match.group(3))
                                    second = int(end_match.group(4))
                                    year = int(date_str[:4])
                                    month = int(date_str[4:6])
                                    day = int(date_str[6:8])
                                    end_time = datetime(year, month, day, hour, minute, second)
                            except:
                                pass
                        
                        # Check for runtime seconds
                        if running_time == 'N/A':
                            runtime_match = runtime_seconds_pattern.search(next_line)
                            if runtime_match:
                                running_time = f"{runtime_match.group(1).strip()} seconds"
                        
                        # Extract screenshot path from log (look for "Screenshot:" line)
                        # Can appear as "Screenshot: path" or in failure message "Screenshot: path"
                        if not screenshot_path and 'Screenshot:' in next_line:
                            # Extract path after "Screenshot:" - handle both formats
                            screenshot_match = re.search(r'Screenshot:\s*(.+?\.png)', next_line)
                            if screenshot_match:
                                screenshot_path = screenshot_match.group(1).strip()
                                # Convert to relative path if it's an absolute path
                                if screenshot_path.startswith('reports'):
                                    screenshot_path = screenshot_path.replace('\\', '/')  # Normalize path separators
                                elif 'reports' in screenshot_path:
                                    # Extract relative path from absolute path
                                    rel_path = screenshot_path.split('reports')[1] if 'reports' in screenshot_path else screenshot_path
                                    screenshot_path = 'reports' + rel_path.replace('\\', '/')
                        
                        # Standard failure message extraction (for non-db_solr_sync tests)
                        if status == 'FAIL' and not failure_message and 'db_solr_sync' not in test_name.lower():
                            if 'Message:' in next_line or 'Error details:' in next_line:
                                # Start capturing from next line
                                capture_lines = []
                                for j in range(i, min(i + 50, len(lines))):
                                    if j < len(lines):
                                        capture_line = lines[j].strip()
                                        # Stop if we hit another section
                                        if j > i and (test_pattern.search(capture_line) or 'Status:' in capture_line):
                                            break
                                        if capture_line and not capture_line.startswith('='):
                                            # Clean up timestamp prefixes
                                            cleaned = re.sub(r'^\d{4}-\d{2}-\d{2}.*?:\s*', '', capture_line)
                                            cleaned = re.sub(r'^E\s+', '', cleaned)
                                            if cleaned:
                                                capture_lines.append(cleaned)
                                                
                                                # Also extract screenshot path from error message if not found yet
                                                if not screenshot_path and 'Screenshot:' in cleaned:
                                                    screenshot_match = re.search(r'Screenshot:\s*(.+?\.png)', cleaned)
                                                    if screenshot_match:
                                                        screenshot_path = screenshot_match.group(1).strip()
                                                        if screenshot_path.startswith('reports'):
                                                            screenshot_path = screenshot_path.replace('\\', '/')
                                                        elif 'reports' in screenshot_path:
                                                            rel_path = screenshot_path.split('reports')[1] if 'reports' in screenshot_path else screenshot_path
                                                            screenshot_path = 'reports' + rel_path.replace('\\', '/')
                                
                                if capture_lines:
                                    failure_message = '\n'.join(capture_lines[:10])  # Limit to 10 lines
                                    error_details = failure_message
                
                # Also check backward for elapsed time (within previous 20 lines)
                if running_time == 'N/A':
                    for back in range(max(0, line_no - 20), line_no):
                        prev_line = lines[back].strip()
                        elapsed_match = elapsed_pattern.search(prev_line)
                        if elapsed_match:
                            running_time = elapsed_match.group(3).strip()
                            break
                        runtime_match = runtime_seconds_pattern.search(prev_line)
                        if runtime_match:
                            running_time = f"{runtime_match.group(1).strip()} seconds"
                            break
                
                # Special handling for db_solr_sync test - read JSON file first, then fallback to log parsing
                if status == 'FAIL' and 'db_solr_sync' in test_name.lower() and not failure_message:
                    error_jobs = []
                    total_jobs = 0
                    error_jobs_count = 0
                    failure_analysis = {}
                    
                    # First, try to read the JSON failure file (most reliable and up-to-date)
                    project_root = get_project_root()
                    json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
                    
                    if json_failure_path.exists():
                        try:
                            # Check if file was modified recently to ensure it's from *this* test run
                            # We only trust the JSON file if it's fresh (within the last 2 hours).
                            file_mtime = datetime.fromtimestamp(json_failure_path.stat().st_mtime)
                            time_diff = abs((test_date - file_mtime).total_seconds())
                            
                            # Use JSON failures ONLY when the file is recent – never reuse old runs.
                            if time_diff < 7200:  # <= 2 hours difference
                                failures_list = []
                                failures_data = None
                                try:
                                    with open(json_failure_path, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                        # Try to parse JSON, but handle incomplete files gracefully
                                        try:
                                            failures_data = json.loads(content)
                                        except json.JSONDecodeError as json_err:
                                            # If JSON is incomplete, try to extract totals from the beginning
                                            print(f"Warning: JSON file is incomplete/corrupted, extracting totals: {json_err}")
                                            # Extract totals from JSON string even if incomplete
                                            total_checked_match = re.search(r'"total_jobs_checked"\s*:\s*(\d+)', content)
                                            total_available_match = re.search(r'"total_jobs_available"\s*:\s*(\d+)', content)
                                            total_failures_match = re.search(r'"total_failures"\s*:\s*(\d+)', content)
                                            
                                            if total_checked_match:
                                                total_jobs = int(total_checked_match.group(1))
                                            elif total_available_match:
                                                total_jobs = int(total_available_match.group(1))
                                            
                                            if total_failures_match:
                                                error_jobs_count = int(total_failures_match.group(1))
                                            
                                            # Try to count failures array items even if incomplete
                                            failures_count = len(re.findall(r'\{\s*"id"\s*:', content))
                                            if failures_count > 0 and error_jobs_count == 0:
                                                error_jobs_count = failures_count
                                            
                                            # Fallback to log parsing for failure details
                                            failures_data = None
                                    
                                    if failures_data:
                                        # Support both old format (list of failures) and new structured format
                                        if isinstance(failures_data, dict):
                                            failures_list = failures_data.get('failures', [])
                                            # Prefer explicit totals from JSON if available
                                            total_jobs = int(failures_data.get('total_jobs_checked') or failures_data.get('total_jobs_available') or total_jobs or 0)
                                            error_jobs_count = int(failures_data.get('total_failures') or len(failures_list))
                                        else:
                                            failures_list = failures_data if isinstance(failures_data, list) else []
                                            error_jobs_count = len(failures_list)
                                        
                                        if failures_list:
                                            # Extract failure analysis
                                            not_found_count = len([f for f in failures_list if "Not Found in Solr" in f.get('msg', '')])
                                            error_count = len([f for f in failures_list if f.get('status') == 'ERROR'])
                                            mismatch_count = len([f for f in failures_list if f.get('status') == 'FAIL' and "Not Found" not in f.get('msg', '')])
                                            failure_analysis = {
                                                'not_found': not_found_count,
                                                'errors': error_count,
                                                'mismatches': mismatch_count
                                            }
                                            
                                            # Convert failures to error_jobs format - only essential error data
                                            for f_item in failures_list:
                                                error_jobs.append({
                                                    'id': str(f_item.get('id', 'N/A')),
                                                    'title': str(f_item.get('db_title', 'N/A'))[:100],  # Limit title
                                                    'error': str(f_item.get('msg', 'N/A'))[:500]  # Limit error message
                                                })
                                except Exception as json_read_err:
                                    print(f"Error reading JSON failure file: {json_read_err}")
                                    failures_data = None
                                
                                if failures_list:
                                    # Extract failure analysis
                                    not_found_count = len([f for f in failures_list if "Not Found in Solr" in f.get('msg', '')])
                                    error_count = len([f for f in failures_list if f.get('status') == 'ERROR'])
                                    mismatch_count = len([f for f in failures_list if f.get('status') == 'FAIL' and "Not Found" not in f.get('msg', '')])
                                    failure_analysis = {
                                        'not_found': not_found_count,
                                        'errors': error_count,
                                        'mismatches': mismatch_count
                                    }
                                    
                                    # Convert failures to error_jobs format
                                    for f_item in failures_list:
                                        error_jobs.append({
                                            'id': str(f_item.get('id', 'N/A')),
                                            'title': str(f_item.get('db_title', 'N/A'))[:100],  # Limit title
                                            'error': str(f_item.get('msg', 'N/A'))[:500]  # Limit error message
                                        })
                        except Exception as e:
                            print(f"Error reading JSON failure file: {e}")
                    
                    # If JSON file doesn't exist or is empty, fallback to parsing log file
                    if not error_jobs:
                        # Search entire log file for tabular format (it's logged much later)
                        for j in range(line_no, len(lines)):
                            if j < len(lines):
                                line = lines[j].strip()
                                # Find "Total Jobs Checked: X" or "Total Jobs: X"
                                if 'Total Jobs Checked:' in line or 'Total Jobs:' in line or 'Jobs Actually Checked:' in line:
                                    match = re.search(r'(?:Total Jobs (?:Checked:)?|Jobs Actually Checked:)\s*(\d+)', line, re.IGNORECASE)
                                    if match:
                                        total_jobs = int(match.group(1))
                                # Find "Total Failures: X" or "Jobs with Errors: X"
                                if 'Total Failures:' in line or 'Jobs with Errors:' in line:
                                    match = re.search(r'(?:Total Failures|Jobs with Errors):\s*(\d+)', line, re.IGNORECASE)
                                    if match:
                                        error_jobs_count = int(match.group(1))
                                # Find table header: "ID | Title | Error" (can be "Error Details" or just "Error")
                                if '|' in line and ('ID' in line or 'id' in line.lower()) and ('Title' in line or 'title' in line.lower()) and ('Error' in line or 'error' in line.lower() or 'error details' in line.lower()):
                                    table_start = j
                                    # Extract table rows
                                    for k in range(table_start + 2, min(table_start + 2000, len(lines))):
                                        if k < len(lines):
                                            table_line = lines[k].strip()
                                            # Stop at separator line (dashes) or end marker
                                            if table_line.startswith('-') and len(table_line) > 20:
                                                continue
                                            if table_line.startswith('=') and len(table_line) > 20:
                                                break
                                            if '|' in table_line and not table_line.startswith('-') and not table_line.startswith('='):
                                                # Parse table row: | ID | Title | Error |
                                                parts = [p.strip() for p in table_line.split('|') if p.strip()]
                                                if len(parts) >= 3:
                                                    # Skip header row if it appears again
                                                    if parts[0].lower() == 'id':
                                                        continue
                                                    job_id = parts[0]
                                                    job_title = parts[1] if len(parts) > 1 else 'N/A'
                                                    error_detail = parts[2] if len(parts) > 2 else 'N/A'
                                                    error_jobs.append({
                                                        'id': job_id,
                                                        'title': job_title[:100] if job_title else 'N/A',  # Limit title
                                                        'error': error_detail[:500] if error_detail else 'N/A'  # Limit error
                                                    })
                                            elif not table_line:
                                                # Empty line might indicate end of table
                                                if error_jobs:
                                                    break
                                    break
                    
                    # Also try to extract total_jobs from log if not found in JSON
                    if total_jobs == 0:
                        for j in range(line_no, min(line_no + 500, len(lines))):
                            if j < len(lines):
                                line = lines[j].strip()
                                if 'Total Jobs Available in DB' in line or 'Jobs Actually Checked:' in line:
                                    match = re.search(r'(\d+)', line)
                                    if match:
                                        total_jobs = int(match.group(1))
                                        break
                    
                    # Format structured error message in new tabular format
                    if error_jobs or total_jobs > 0 or error_jobs_count > 0:
                        # Build summary section
                        structured_msg = "=" * 120 + "\n"
                        structured_msg += "SOLR SYNC FAILURE SUMMARY\n"
                        structured_msg += "=" * 120 + "\n"
                        if total_jobs > 0:
                            structured_msg += f"Total Jobs Available in DB (last 24h): {total_jobs}\n"
                        structured_msg += f"Jobs Actually Checked: {total_jobs if total_jobs > 0 else len(error_jobs) if error_jobs else 0}\n"
                        structured_msg += f"Total Failures: {error_jobs_count if error_jobs_count > 0 else len(error_jobs)}\n"
                        if error_jobs_count > 0 and total_jobs > 0:
                            success_rate = ((total_jobs - error_jobs_count) / total_jobs * 100) if total_jobs > 0 else 0
                            structured_msg += f"Success Rate: {success_rate:.2f}%\n"
                        structured_msg += "=" * 120 + "\n"
                        
                        # Add failure analysis if available
                        if failure_analysis:
                            structured_msg += "\nFailure Analysis:\n"
                            structured_msg += f"  - Not Found in Solr: {failure_analysis.get('not_found', 0)} jobs\n"
                            structured_msg += f"  - Field Mismatches: {failure_analysis.get('mismatches', 0)} jobs\n"
                            structured_msg += f"  - Query Errors: {failure_analysis.get('errors', 0)} jobs\n"
                            structured_msg += "=" * 120 + "\n\n"
                        
                        # Build table header
                        id_width = 12
                        title_width = 50
                        error_width = 50
                        header_line = f"{'ID':<{id_width}} | {'Title':<{title_width}} | {'Error':<{error_width}}"
                        separator = "-" * len(header_line)
                        
                        structured_msg += separator + "\n"
                        structured_msg += header_line + "\n"
                        structured_msg += separator + "\n"
                        
                        # Add table rows (limit to first 1000 for performance)
                        for job in error_jobs[:1000]:
                            id_str = str(job['id'])[:id_width]
                            title_str = str(job['title'])[:title_width]
                            error_str = str(job['error'])[:error_width]
                            structured_msg += f"{id_str:<{id_width}} | {title_str:<{title_width}} | {error_str:<{error_width}}\n"
                        
                        if len(error_jobs) > 1000:
                            structured_msg += f"\n... and {len(error_jobs) - 1000} more failures (see reports/db_solr_sync_failures.json for complete list)\n"
                        
                        structured_msg += separator + "\n"
                        structured_msg += f"\n📄 Complete failure details saved in: reports/db_solr_sync_failures.json\n"
                        failure_message = structured_msg
                        error_details = structured_msg
                
                # Format datetime strings
                datetime_str = test_date.isoformat()
                if end_time:
                    datetime_str = f"{test_date.isoformat()} to {end_time.isoformat()}"
                
                test_data = {
                    'test_name': test_name,
                    'status': status,
                    'date': test_date.strftime('%Y-%m-%d'),
                    'datetime': datetime_str,
                    'start_time': start_time_str or test_date.strftime('%Y%m%d %H:%M:%S'),
                    'end_time': end_time_str or '',
                    'running_time': running_time,
                    'line_no': line_no
                }
                
                # Add screenshot path if found
                if screenshot_path:
                    test_data['screenshot_path'] = screenshot_path
                
                # Add totals if available (from JSON or log parsing) - always include even if 0
                test_data['total_jobs'] = total_jobs  # Always include, even if 0
                test_data['error_jobs_count'] = error_jobs_count  # Always include, even if 0
                
                # CRITICAL: Only store error_jobs if there are actual failures
                # Limit to error_jobs_count to prevent storing all jobs instead of just failures
                if error_jobs and len(error_jobs) > 0:
                    # If error_jobs_count is set and smaller than error_jobs length, limit to that count
                    # This prevents storing all jobs when we should only store failures
                    if error_jobs_count > 0 and len(error_jobs) > error_jobs_count:
                        # Limit to actual error count (take first N error jobs)
                        test_data['error_jobs'] = error_jobs[:error_jobs_count]
                    else:
                        test_data['error_jobs'] = error_jobs
                
                # Add failure information if available
                # ONLY store failure details if there are actual errors
                if status == 'FAIL' and failure_message and error_jobs_count > 0:
                    test_data['failure_message'] = failure_message
                    test_data['error_details'] = error_details
                
                tests.append(test_data)
    except Exception as e:
        print(f"Error parsing log file {log_file_path}: {e}")
        import traceback
        traceback.print_exc()
    
    return tests


def _find_latest_test_in_log(module: str, test_case: str) -> Optional[Dict]:
    """Find the latest occurrence of a specific test in the log tail (fast path)."""
    module_config = MODULES.get(module)
    if not module_config:
        return None

    log_file_path = get_project_root() / module_config['log_file']
    if not log_file_path.exists():
        return None

    try:
        file_size = log_file_path.stat().st_size
        # Skip tail scan for very large logs to avoid timeouts (update runs in background).
        if file_size > 100 * 1024 * 1024:
            return None
        tail_size = 1 * 1024 * 1024  # 1MB tail for quick scan
        with open(log_file_path, 'rb') as f:
            f.seek(max(0, file_size - tail_size), os.SEEK_SET)
            raw = f.read()
        lines = raw.decode('utf-8', errors='ignore').splitlines()

        log_date = extract_date_from_log(lines) or datetime.fromtimestamp(log_file_path.stat().st_mtime)
        test_pattern = re.compile(rf"TEST\s+{re.escape(test_case)}:\s*(PASS|FAIL|SKIP)", re.IGNORECASE)

        for line_no, line in enumerate(reversed(lines), 1):
            match = test_pattern.search(line)
            if match:
                status = match.group(1).upper()
                return {
                    'test_name': test_case,
                    'status': status,
                    'date': log_date.strftime('%Y-%m-%d'),
                    'datetime': log_date.isoformat(),
                    'running_time': 'N/A',
                    'line_no': line_no
                }
    except Exception as e:
        print(f"Error scanning log tail for {test_case}: {e}")

    return None


def _build_history_from_log_tail(module: str, test_case: str) -> List[Dict]:
    """Build per-day history for a test by scanning the log tail (fast, no full parse)."""
    module_config = MODULES.get(module)
    if not module_config:
        return []

    log_file_path = get_project_root() / module_config['log_file']
    if not log_file_path.exists():
        return []

    try:
        file_size = log_file_path.stat().st_size
        tail_size = 25 * 1024 * 1024  # 25MB tail for recent runs
        with open(log_file_path, 'rb') as f:
            f.seek(max(0, file_size - tail_size), os.SEEK_SET)
            raw = f.read()
        lines = raw.decode('utf-8', errors='ignore').splitlines()

        entries: List[Dict] = []
        current_test = None
        last_start_dt = None
        last_elapsed = 'N/A'

        start_line_pattern = re.compile(
            r"Start\s*/\s*End\s*/\s*Elapsed:\s*(\d{8})\s+(\d{2}):(\d{2}):(\d{2})[^/]+/[^/]+/\s*([0-9:.]+)",
            re.IGNORECASE
        )
        header_pattern = re.compile(r"^TEST\s+(test_[^:]+)\s*$", re.IGNORECASE)
        result_pattern = re.compile(r"^TEST\s+(test_[^:]+):\s*(PASS|FAIL|SKIP)", re.IGNORECASE)

        for line in lines:
            header_match = header_pattern.match(line)
            if header_match:
                current_test = header_match.group(1).strip()
                last_start_dt = None
                last_elapsed = 'N/A'
                continue

            start_match = start_line_pattern.search(line)
            if start_match and current_test:
                date_str = start_match.group(1)
                hour = int(start_match.group(2))
                minute = int(start_match.group(3))
                second = int(start_match.group(4))
                last_elapsed = start_match.group(5).strip()
                last_start_dt = datetime(
                    int(date_str[:4]),
                    int(date_str[4:6]),
                    int(date_str[6:8]),
                    hour,
                    minute,
                    second
                )
                continue

            result_match = result_pattern.match(line)
            if result_match:
                name = result_match.group(1).strip()
                status = result_match.group(2).upper()
                if name == test_case:
                    entry_dt = last_start_dt or extract_date_from_log(lines) or datetime.fromtimestamp(log_file_path.stat().st_mtime)
                    entries.append({
                        'test_name': test_case,
                        'status': status,
                        'date': entry_dt.strftime('%Y-%m-%d'),
                        'datetime': entry_dt.isoformat(),
                        'running_time': last_elapsed,
                        'line_no': 0
                    })
                current_test = None
                last_start_dt = None
                last_elapsed = 'N/A'

        # Keep the latest entry per date
        by_date: Dict[str, Dict] = {}
        for entry in entries:
            date_key = entry.get('date')
            if not date_key:
                continue
            if date_key not in by_date:
                by_date[date_key] = entry
                continue
            if entry.get('datetime', '') > by_date[date_key].get('datetime', ''):
                by_date[date_key] = entry

        return list(by_date.values())
    except Exception as e:
        print(f"Error building log tail history for {test_case}: {e}")
        return []


def is_test_for_module(test_name: str, module: str) -> bool:
    """Check if a test belongs to a specific module based on naming patterns"""
    test_lower = test_name.lower()
    # If we have an allowlist from test files, use it for strict isolation
    allowed_tests = get_allowed_tests(module)
    if allowed_tests:
        return test_name in allowed_tests
    
    if module == 'benchsale_admin':
        # Admin tests: t1_xx pattern or 'admin' in name
        return 't1_' in test_lower or 'admin' in test_lower
    
    elif module == 'benchsale_recruiter':
        # Recruiter tests: t2_xx pattern or 'recruiter' in name
        return 't2_' in test_lower or 'recruiter' in test_lower
    
    elif module == 'benchsale_test':
        # Main test log includes both admin and recruiter tests
        # EXCLUDE Employer/JobSeeker tests explicitly to prevent overlap
        if 'employer' in test_lower or 'jobseeker' in test_lower or 'js' in test_lower and 'json' not in test_lower:
            return False
            
        return 't1_' in test_lower or 't2_' in test_lower or 'admin' in test_lower or 'recruiter' in test_lower
    
    elif module == 'employer':
        # Employer tests: STRICT filtering - exclude ALL tests that belong to other modules
        # First, exclude BenchSale tests (but NOT employer tests that also use t1_/t2_ patterns)
        # Only exclude if it has BenchSale-specific keywords (admin/recruiter) along with t1_/t2_
        if ('admin' in test_lower or 'recruiter' in test_lower) and ('t1_' in test_lower or 't2_' in test_lower):
            return False  # These are benchsale tests (has admin/recruiter + t1_/t2_ pattern)
        # Exclude if it has benchsale in the name
        if 'benchsale' in test_lower:
            return False  # BenchSale test
        
        # Exclude jobseeker-specific tests
        if 'js_from' in test_lower:
            return False  # "js_from" = jobseeker applying from home page = jobseeker test
        
        # IMPORTANT: Tests with "job_posting_displayed_in_js_dashboard" are EMPLOYER tests
        # These verify that employer's job postings appear in jobseeker dashboard (employer action)
        if 'job_posting_displayed_in_js' in test_lower or 'verification_of_job_posting_displayed_in_js' in test_lower:
            return True  # Employer verifying their posting appears in JS dashboard = employer test
        
        # Employer actions on jobseekers (shortlisting, applicant management, etc.)
        employer_actions = ['shortlisting', 'applicant', 'closing', 'post_a_job', 'hotlist', 'hot_list']
        if any(action in test_lower for action in employer_actions):
            return True  # Employer actions = employer test
        
        # If test has "js_dashboard" but is about jobseeker actions (not employer verification), exclude
        if 'js_dashboard' in test_lower:
            if 'verification' in test_lower or 'displayed' in test_lower:
                return True  # Employer verifying posting appears = employer test
            if 'jobseeker' in test_lower:
                return False  # Has "jobseeker" with js_dashboard = jobseeker test
        
        # If test has "js" but also has employer-specific keywords, it's employer
        if 'js' in test_lower and ('employer' in test_lower or 'emp' in test_lower):
            return True  # Has "js" with employer context = employer test
        
        # If test has employer/emp keywords, it's likely an employer test
        if 'employer' in test_lower or 'emp' in test_lower:
            return True  # Has employer keywords = employer test
        
        # If test is from employer.log and doesn't have jobseeker keywords, it's an employer test
        # But exclude if it has clear jobseeker indicators
        if 'jobseeker' in test_lower and 'js_from' not in test_lower:
            # Has "jobseeker" but not "js_from" - might be employer test about jobseekers
            # Check if it's about employer actions
            if any(action in test_lower for action in employer_actions):
                return True  # Employer action on jobseekers = employer test
        
        # IMPORTANT: If test is in employer.log file, it's likely an employer test
        # Only exclude if it clearly belongs to another module
        # This ensures we don't filter out valid employer tests that don't have explicit keywords
        # Default: if from employer context and no clear exclusion, it's an employer test
        return True
    
    elif module == 'jobseeker':
        # JobSeeker tests: STRICT filtering - exclude ALL tests that belong to other modules
        # First, exclude BenchSale tests (but NOT jobseeker tests that also use t1_ pattern)
        # Only exclude if it has BenchSale-specific keywords (admin/recruiter) along with t1_/t2_
        if ('admin' in test_lower or 'recruiter' in test_lower) and ('t1_' in test_lower or 't2_' in test_lower):
            return False  # These are benchsale tests (has admin/recruiter + t1_/t2_ pattern)
        # Exclude if it has benchsale in the name
        if 'benchsale' in test_lower:
            return False  # BenchSale test
        
        # Exclude employer-specific features
        if 'hotlist' in test_lower or 'hot_list' in test_lower:
            return False  # Hotlist = employer feature
        
        # CRITICAL: Exclude ALL employer tests - even if they mention "js"
        # Employer tests that mention "js" are still employer tests (e.g., "job_posting_displayed_in_js_dashboard")
        employer_keywords = ['job_posting_displayed_in_js', 'verification_of_job_posting_displayed_in_js',
                           'shortlisting', 'applicant', 'closing', 'post_a_job', 'posting_displayed']
        if any(keyword in test_lower for keyword in employer_keywords):
            return False  # These are employer tests, not jobseeker
        
        # Exclude tests with employer/emp keywords (unless clearly jobseeker context)
        if 'employer' in test_lower or 'emp' in test_lower:
            # Only allow if it's clearly a jobseeker action (e.g., "verify_the_parsed_resume_in_emp" with js_dashboard)
            # But exclude if it's about employer actions
            if 'js_dashboard' not in test_lower and 'jobseeker' not in test_lower:
                return False  # Has employer/emp but no clear jobseeker context = employer test
        
        # JobSeeker tests should have "js", "jobseeker", or be from jobseeker test files
        # Tests without these keywords might be from other modules
        if 'js' not in test_lower and 'jobseeker' not in test_lower:
            # No js/jobseeker keyword - check if it's clearly NOT a jobseeker test
            if 'employer' in test_lower or 'emp' in test_lower:
                return False  # Has employer keywords = employer test
            if 'home_page' in test_lower and 'js_from' not in test_lower:
                # "home_page" without "js_from" might be employer test
                return False
            # If no clear indicators and it's from jobseeker.log, allow it (might be jobseeker test)
            # But be conservative - only allow if it doesn't have any employer/benchsale keywords
            return True
        
        # If test has "js" or "jobseeker", it's likely a jobseeker test
        # But double-check it's not an employer test that mentions js
        if 'js' in test_lower:
            # Exclude if it's clearly an employer action (already checked above with employer_keywords)
            # If we reach here, it's a jobseeker test
            return True
        
        # If test has "jobseeker" keyword, it's definitely a jobseeker test
        if 'jobseeker' in test_lower:
            return True
        
        # Default: if unsure and no clear exclusion criteria, exclude it (be conservative)
        return False
    
    return True  # Default: include if unsure


def get_all_test_cases(module: str) -> List[str]:
    """Get all test case names for a module - ONLY related tests from that module's log file
    OPTIMIZED: Uses cached history data first, then log file parsing (non-blocking for large files)
    """
    module_config = MODULES.get(module)
    if not module_config:
        return []
    
    test_cases = set()
    project_root = get_project_root()
    
    # OPTIMIZATION: Check historical data FIRST (fast, already parsed)
    # This avoids parsing large log files synchronously
    history = load_historical_data(module)
    for test_name in history.keys():
        if is_test_for_module(test_name, module):
            test_cases.add(test_name)
    
    # Secondary: Check test files (for tests that haven't run yet)
    for test_file in module_config['test_files']:
        test_file_path = project_root / test_file
        if test_file_path.exists():
            try:
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract test function names - improved pattern
                    test_func_pattern = re.compile(r'def\s+(test_[a-zA-Z0-9_]+)', re.IGNORECASE)
                    matches = test_func_pattern.findall(content)
                    for match in matches:
                        # For ALL modules, filter by is_test_for_module to ensure correct data isolation
                        if is_test_for_module(match, module):
                            test_cases.add(match)
            except Exception as e:
                print(f"Error reading test file {test_file_path}: {e}")
    
    # Last resort: Parse log file (only if history is empty and we need fresh data)
    # For large log files, this is done in background by update_historical_data
    # Here we only parse if absolutely necessary (history empty)
    if not test_cases:
        log_file_path = project_root / module_config['log_file']
        if log_file_path.exists():
            try:
                # For very large files, only read last portion to find recent tests
                # This is much faster than reading entire file
                file_size = log_file_path.stat().st_size
                if file_size > 50 * 1024 * 1024:  # If file > 50MB
                    # Read last 10MB of file (most recent tests)
                    with open(log_file_path, 'rb') as f:
                        f.seek(max(0, file_size - 10 * 1024 * 1024))
                        lines = f.read().decode('utf-8', errors='ignore').split('\n')
                else:
                    # Small file, read normally
                    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                
                # Quick pattern search for test names (faster than full parse)
                test_pattern = re.compile(r'TEST\s+(test_[^:]+):\s*(PASS|FAIL|SKIP)', re.IGNORECASE)
                for line in lines:
                    match = test_pattern.search(line)
                    if match:
                        test_name = match.group(1).strip()
                        if is_test_for_module(test_name, module):
                            test_cases.add(test_name)
            except Exception as e:
                print(f"Error reading log file {log_file_path}: {e}")
    
    return sorted(list(test_cases))
    
    # Secondary source: test files (for tests that haven't run yet)
    for test_file in module_config['test_files']:
        test_file_path = project_root / test_file
        if test_file_path.exists():
            try:
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract test function names - improved pattern
                    test_func_pattern = re.compile(r'def\s+(test_[a-zA-Z0-9_]+)', re.IGNORECASE)
                    matches = test_func_pattern.findall(content)
                    for match in matches:
                        # For ALL modules, filter by is_test_for_module to ensure correct data isolation
                        if is_test_for_module(match, module):
                            test_cases.add(match)
            except Exception as e:
                print(f"Error reading test file {test_file_path}: {e}")
    
    # Also check historical data - FILTER by module
    history = load_historical_data(module)
    for test_name in history.keys():
        # For ALL modules, filter by is_test_for_module to ensure correct data isolation
        if is_test_for_module(test_name, module):
            test_cases.add(test_name)
    
    return sorted(list(test_cases))


def _cleanup_old_data(history: Dict, module: str, save_changes: bool = False) -> int:
    """Clean up old data (older than 7 days) from history
    Returns: Number of entries deleted
    save_changes: If True, actually modify the history dict. If False, just return count."""
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cutoff_datetime = datetime.now() - timedelta(days=7)
    total_deleted = 0
    
    for test_name in list(history.keys()):
        original_count = len(history[test_name])
        
        # Filter to keep only last 7 days - check both date and datetime
        recent_entries = []
        for entry in history[test_name]:
            entry_date = entry.get('date', '')
            entry_datetime_str = entry.get('datetime', '')
            
            # Check date first
            if entry_date and entry_date >= cutoff_date:
                recent_entries.append(entry)
            elif entry_datetime_str:
                # Also check datetime if date is missing or old
                try:
                    # Handle " to " format
                    if ' to ' in entry_datetime_str:
                        entry_datetime_str = entry_datetime_str.split(' to ')[0].strip()
                    entry_dt = datetime.fromisoformat(entry_datetime_str.replace('Z', '+00:00') if 'Z' in entry_datetime_str else entry_datetime_str)
                    if entry_dt >= cutoff_datetime:
                        # Update date field if missing
                        if not entry_date:
                            entry['date'] = entry_dt.strftime('%Y-%m-%d')
                        recent_entries.append(entry)
                except:
                    # If datetime parsing fails, skip this entry (it's likely old or invalid)
                    pass
        
        if save_changes:
            # For each day, keep only the LATEST run (by datetime)
            entries_by_date = {}
            for entry in recent_entries:
                entry_date = entry.get('date', '')
                if not entry_date:
                    continue
                
                entry_datetime_str = entry.get('datetime', entry.get('date', ''))
                # Normalize datetime (remove " to " if present)
                if entry_datetime_str and ' to ' in entry_datetime_str:
                    entry_datetime_str = entry_datetime_str.split(' to ')[0].strip()
                
                # If we already have an entry for this date, compare datetimes
                if entry_date in entries_by_date:
                    existing_entry = entries_by_date[entry_date]
                    existing_datetime_str = existing_entry.get('datetime', existing_entry.get('date', ''))
                    if existing_datetime_str and ' to ' in existing_datetime_str:
                        existing_datetime_str = existing_datetime_str.split(' to ')[0].strip()
                    
                    # Compare datetimes to keep the latest
                    try:
                        if entry_datetime_str and existing_datetime_str:
                            entry_dt = datetime.fromisoformat(entry_datetime_str.replace('Z', '+00:00') if 'Z' in entry_datetime_str else entry_datetime_str)
                            existing_dt = datetime.fromisoformat(existing_datetime_str.replace('Z', '+00:00') if 'Z' in existing_datetime_str else existing_datetime_str)
                            if entry_dt > existing_dt:
                                entries_by_date[entry_date] = entry  # Replace with newer entry
                        elif entry_datetime_str:
                            entries_by_date[entry_date] = entry  # New entry has datetime, existing doesn't
                    except Exception:
                        # If datetime comparison fails, keep the one with more complete data
                        if entry.get('datetime') and not existing_entry.get('datetime'):
                            entries_by_date[entry_date] = entry
                else:
                    # First entry for this date
                    entries_by_date[entry_date] = entry
            
            # Convert back to list and sort by date descending
            history[test_name] = list(entries_by_date.values())
            history[test_name].sort(key=lambda x: (x.get('date', ''), x.get('datetime', '')), reverse=True)
            
            # Remove test name if no data left
            if not history[test_name]:
                del history[test_name]
        
        deleted_count = original_count - len(recent_entries) if not save_changes else (original_count - len(history.get(test_name, [])))
        total_deleted += deleted_count
    
    return total_deleted


def load_historical_data(module: str, force_reload: bool = False) -> Dict:
    """Load historical data for a module - with fallback to backup if main file is corrupted
    CRITICAL: Automatically cleans data to ensure only module-specific tests are included
    CRITICAL: Automatically removes data older than 7 days to save storage
    force_reload: If True, always read from disk (ignore any in-memory cache)"""
    history_file = HISTORY_DIR / f"{module}_history.json"
    backup_file = HISTORY_DIR / f"{module}_history.json.backup"
    
    data = {}
    loaded_from_backup = False
    
    # CRITICAL: If force_reload is True, always read fresh from disk
    # This ensures API always gets latest data, especially for db_solr_sync
    if force_reload:
        # Clear any potential in-memory cache by forcing fresh read
        pass  # Will read from disk below
    
    # Try to load main file first
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Validate data structure
                if isinstance(data, dict):
                    pass  # Continue to cleaning
                else:
                    print(f"Warning: {history_file} has invalid structure, trying backup...")
                    data = {}
        except json.JSONDecodeError as e:
            print(f"Error parsing {history_file}: {e}, trying backup...")
            data = {}
        except Exception as e:
            print(f"Error loading history file {history_file}: {e}, trying backup...")
            data = {}
    
    # Fallback to backup file
    if not data and backup_file.exists():
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    print(f"Loaded {module} history from backup file")
                    loaded_from_backup = True
        except Exception as e:
            print(f"Error loading backup file {backup_file}: {e}")
            data = {}
    
    # CRITICAL: Clean data immediately after loading - remove any tests that don't belong to this module
    # This ensures complete data isolation even if history files have old/corrupted data
    # BUT: Only filter in memory during reads (force_reload=False) to avoid data loss
    # Only actually delete from file during updates (force_reload=True)
    if data:
        tests_to_remove = []
        for test_name in list(data.keys()):
            if not is_test_for_module(test_name, module):
                tests_to_remove.append(test_name)
                print(f"AUTO-CLEAN: Marked '{test_name}' for removal from {module} history (doesn't belong to this module)")
        
        # CRITICAL: Clean up old data (>7 days) - always do this to save storage
        old_data_deleted = _cleanup_old_data(data, module, save_changes=force_reload)
        if old_data_deleted > 0 and force_reload:
            print(f"AUTO-CLEAN: Removed {old_data_deleted} old entries (>7 days) from {module} history")
        
        # CRITICAL: Only save cleaned data if force_reload is True (during updates)
        # During normal reads (force_reload=False), filter in memory but DON'T delete from data
        # This prevents data loss when API is called multiple times
        if (tests_to_remove or old_data_deleted > 0) and force_reload:
            # Only delete during updates, not during reads
            for test_name in tests_to_remove:
                del data[test_name]
            # Save cleaned data immediately (only during updates, not during reads)
            try:
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                if loaded_from_backup:
                    # Also restore backup
                    import shutil
                    shutil.copy2(history_file, backup_file)
                print(f"AUTO-CLEAN: Cleaned {module} history - removed {len(tests_to_remove)} invalid tests and {old_data_deleted} old entries")
            except Exception as e:
                print(f"Warning: Could not save cleaned history for {module}: {e}")
        # NOTE: During reads (force_reload=False), we DON'T delete from data dict
        # This ensures API calls don't lose data even if auto-clean marks tests for removal
        elif loaded_from_backup:
            # Restore backup to main file if we loaded from backup
            import shutil
            shutil.copy2(backup_file, history_file)
    
    return data if data else {}


def save_historical_data(module: str, data: Dict):
    """Save historical data for a module - with backup to prevent data loss
    CRITICAL: Automatically cleans old data (>7 days) before saving to save storage"""
    history_file = HISTORY_DIR / f"{module}_history.json"
    backup_file = HISTORY_DIR / f"{module}_history.json.backup"
    
    try:
        # CRITICAL: Clean up old data before saving to ensure storage doesn't grow
        # Make a copy to avoid modifying the original dict during cleanup
        data_to_save = {k: v.copy() if isinstance(v, list) else v for k, v in data.items()}
        old_data_deleted = _cleanup_old_data(data_to_save, module, save_changes=True)
        if old_data_deleted > 0:
            print(f"Storage cleanup: Removed {old_data_deleted} old entries (>7 days) before saving {module} history")
        
        # Create backup of existing file before overwriting
        if history_file.exists():
            import shutil
            shutil.copy2(history_file, backup_file)
        
        # Save cleaned data
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history file {history_file}: {e}")
        # Try to restore from backup if save failed
        if backup_file.exists():
            try:
                import shutil
                shutil.copy2(backup_file, history_file)
                print(f"Restored {module} history from backup due to save error")
            except:
                pass


def update_historical_data(module: str):
    """Update historical data from current log file"""
    module_config = MODULES.get(module)
    if not module_config:
        return
    
    project_root = get_project_root()
    log_file_path = project_root / module_config['log_file']
    
    if not log_file_path.exists():
        return
    
    # Parse current log file (date will be extracted from log content)
    current_tests = parse_log_file(log_file_path)
    
    # SPECIAL CASE: For db_solr_sync test, also check JSON file for latest failure data
    # This ensures we always have the most recent failure data even if log parsing missed it
    db_solr_test_from_json = None
    if module == 'jobseeker':
        json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
        if json_failure_path.exists():
            try:
                # Check if JSON file is recent (within last 24 hours)
                file_mtime = datetime.fromtimestamp(json_failure_path.stat().st_mtime)
                if (datetime.now() - file_mtime).total_seconds() < 86400:  # 24 hours
                    with open(json_failure_path, 'r', encoding='utf-8') as f:
                        failures_data = json.load(f)
                    
                    # Check if we have a db_solr_sync test entry
                    db_solr_test = next((t for t in current_tests if 'db_solr_sync' in t.get('test_name', '').lower()), None)
                    
                    total_jobs = failures_data.get('total_jobs_checked', failures_data.get('total_jobs_available', 0))
                    error_count = failures_data.get('total_failures', 0)
                    failures_list = failures_data.get('failures', [])

                    # Create or update test entry with JSON data (single source of truth)
                    test_date = file_mtime.strftime('%Y-%m-%d')
                    stable_datetime = file_mtime.isoformat()  # Stable source - test completion time
                    db_solr_test = db_solr_test or {}
                    db_solr_test.update({
                        'test_name': 'test_t1_09_db_solr_sync_verification',
                        'status': 'FAIL' if error_count > 0 else 'PASS',
                        'date': test_date,
                        'datetime': stable_datetime,
                        'start_time': file_mtime.strftime('%Y%m%d %H:%M:%S'),
                        'end_time': '',
                        'running_time': 'N/A',
                        'line_no': 0,
                        'total_jobs': total_jobs,
                        'error_jobs_count': error_count,
                        'error_jobs': [
                            {
                                'id': str(f.get('id', 'N/A')),
                                'title': str(f.get('db_title', 'N/A'))[:100],
                                'error': str(f.get('msg', 'N/A'))[:500]
                            }
                            for f in failures_list[:error_count]
                        ],
                        'stable_datetime': stable_datetime
                    })

                    # Build failure_message from JSON data (always overwrite to avoid old data)
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
                    db_solr_test['failure_message'] = structured_msg[:2000]
                    db_solr_test['error_details'] = structured_msg[:2000]

                    # Store for later - we'll inject after removing log-parsed entries
                    db_solr_test_from_json = db_solr_test
            except Exception as e:
                print(f"Warning: Could not read JSON failure file for db_solr_sync: {e}")
    
    # Load existing history
    history = load_historical_data(module)
    
    # CRITICAL: For db_solr_sync test, preserve existing JSON-based data
    # Only clear if we have newer JSON data to replace it with
    # This prevents data loss when update_historical_data is called multiple times
    db_solr_existing_data = {}
    for test_name_key in list(history.keys()):
        if 'db_solr_sync' in test_name_key.lower() and history[test_name_key]:
            # Preserve existing entry if it has failure data
            existing_entry = history[test_name_key][0] if history[test_name_key] else None
            if existing_entry and (existing_entry.get('error_jobs_count', 0) > 0 or (existing_entry.get('error_jobs') and len(existing_entry.get('error_jobs', [])) > 0)):
                db_solr_existing_data[test_name_key] = existing_entry
                print(f"PRESERVE: Keeping existing failure data for {test_name_key} (failures: {existing_entry.get('error_jobs_count', 0)})")
    
    # CRITICAL: For db_solr_sync test, REMOVE ALL entries from current_tests that come from log parsing
    # We ONLY want entries from JSON file, not from log parsing
    # This prevents log parsing from overwriting correct JSON data
    if module == 'jobseeker':
        # Remove ALL db_solr_sync entries from log parsing - we'll add them from JSON only
        current_tests = [t for t in current_tests if 'db_solr_sync' not in t.get('test_name', '').lower()]
        if db_solr_test_from_json:
            # CRITICAL: Check if we should update or preserve existing data
            test_name_json = db_solr_test_from_json.get('test_name', '')
            should_add_json = True
            if test_name_json in db_solr_existing_data:
                existing_entry = db_solr_existing_data[test_name_json]
                json_datetime = db_solr_test_from_json.get('datetime', '')
                existing_datetime = existing_entry.get('datetime', existing_entry.get('date', ''))
                if existing_datetime and json_datetime:
                    try:
                        if ' to ' in existing_datetime:
                            existing_datetime = existing_datetime.split(' to ')[0].strip()
                        if ' to ' in json_datetime:
                            json_datetime = json_datetime.split(' to ')[0].strip()
                        existing_dt = datetime.fromisoformat(existing_datetime.replace('Z', '+00:00') if 'Z' in existing_datetime else existing_datetime)
                        json_dt = datetime.fromisoformat(json_datetime.replace('Z', '+00:00') if 'Z' in json_datetime else json_datetime)
                        # Only update if JSON is significantly newer (more than 1 minute)
                        if (json_dt - existing_dt).total_seconds() < 60:
                            print(f"PRESERVE: JSON data is not significantly newer, keeping existing data for {test_name_json}")
                            should_add_json = False
                    except Exception as e:
                        print(f"PRESERVE: Datetime comparison failed for {test_name_json}: {e} - using JSON data")
            if should_add_json:
                current_tests.append(db_solr_test_from_json)
            else:
                # Restore existing data to history so it's preserved
                if test_name_json not in history:
                    history[test_name_json] = []
                history[test_name_json] = [db_solr_existing_data[test_name_json]]
                print(f"PRESERVE: Restored existing failure data for {test_name_json}")
    
    # CRITICAL: For db_solr_sync, check JSON file FIRST and update test status if needed
    # This ensures failures from JSON are always reflected in history
    json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
    if json_failure_path.exists():
        try:
            with open(json_failure_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            total_failures = json_data.get('total_failures', 0)
            total_jobs = json_data.get('total_jobs_checked', json_data.get('total_jobs_available', 0))
            
            # Find db_solr_sync test in current_tests and update its status if JSON shows failures
            for test in current_tests:
                if 'db_solr_sync' in test.get('test_name', '').lower():
                    # If JSON has failures, ensure test status is FAIL
                    if total_failures > 0:
                        test['status'] = 'FAIL'
                        test['error_jobs_count'] = total_failures
                        test['total_jobs'] = total_jobs
                        print(f"JSON-UPDATE: Updated {test['test_name']} status to FAIL (failures: {total_failures})")
        except Exception as e:
            print(f"Warning: Could not read JSON file for db_solr_sync status update: {e}")
    
    # Update history with current data - ONLY for tests belonging to this module
    # IMPORTANT: For Employer/JobSeeker, ALL tests in their log files belong to them
    # For BenchSale, filter by pattern (t1_ for admin, t2_ for recruiter)
    for test in current_tests:
        test_name = test['test_name']
        
        # CRITICAL: Filter ALL tests to ensure data isolation - NO EXCEPTIONS
        # Even if a test is in the log file, verify it belongs to this module
        # This prevents cross-contamination between modules
        if not is_test_for_module(test_name, module):
            # Test doesn't belong to this module - skip it
            print(f"Filtered out '{test_name}' from {module} (belongs to another module)")
            continue
        
        # CRITICAL: For db_solr_sync, ALWAYS use JSON file data if it exists
        # Skip log parsing entirely for db_solr_sync - JSON file is the single source of truth
        if 'db_solr_sync' in test_name.lower():
            json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
            if json_failure_path.exists():
                try:
                    json_mtime = datetime.fromtimestamp(json_failure_path.stat().st_mtime)
                    # Check if existing entry in history has data from JSON (has error_jobs or error_jobs_count > 0)
                    if test_name in history and history[test_name]:
                        existing_entry = history[test_name][0] if history[test_name] else None
                        if existing_entry:
                            existing_datetime_str = existing_entry.get('datetime', existing_entry.get('date', ''))
                            if existing_datetime_str:
                                try:
                                    # Normalize existing datetime
                                    if ' to ' in existing_datetime_str:
                                        existing_datetime_str = existing_datetime_str.split(' to ')[0].strip()
                                    existing_dt = datetime.fromisoformat(existing_datetime_str.replace('Z', '+00:00') if 'Z' in existing_datetime_str else existing_datetime_str)
                                    # CRITICAL: If existing entry has failure data and JSON file is not newer, preserve existing data
                                    # Only update if JSON file is significantly newer (more than 1 minute) to prevent overwriting
                                    time_diff = (json_mtime - existing_dt).total_seconds()
                                    if time_diff < 60 and (existing_entry.get('error_jobs_count', 0) > 0 or (existing_entry.get('error_jobs') and len(existing_entry.get('error_jobs', [])) > 0)):
                                        print(f"SKIP-LOG-PARSE: Preserving JSON-based data for {test_name} (JSON: {json_mtime.isoformat()}, existing: {existing_dt.isoformat()}, diff: {time_diff}s)")
                                        continue  # Skip this test - keep existing JSON-based data
                                except Exception as e:
                                    print(f"SKIP-LOG-PARSE: Datetime comparison failed for {test_name}: {e} - preserving existing data")
                                    continue  # If comparison fails, preserve existing data
                            elif existing_entry.get('error_jobs_count', 0) > 0 or (existing_entry.get('error_jobs') and len(existing_entry.get('error_jobs', [])) > 0):
                                # Has failure data but no datetime - preserve it
                                print(f"SKIP-LOG-PARSE: Preserving existing failure data for {test_name} (no datetime)")
                                continue
                except Exception as e:
                    print(f"SKIP-LOG-PARSE: JSON check failed for {test_name}: {e} - proceeding with log parse")
            
            # Only clear history if we're going to add new data from JSON (not from log parsing)
            # Don't clear if we're skipping log parsing
            if test_name in history:
                old_count = len(history[test_name])
                if old_count > 0:
                    # Only clear if we're actually going to process this test
                    # (This will be handled by the JSON injection logic above)
                    pass  # Don't clear here - let JSON injection handle it
            else:
                history[test_name] = []  # Initialize as empty list
        
        if test_name not in history:
            history[test_name] = []
        
        # Check if this test result already exists (same date)
        test_date = test['date']
        existing = next(
            (t for t in history[test_name] if t['date'] == test_date),
            None
        )
        
        if existing:
            # CRITICAL: For ALL tests, ALWAYS replace same-day entry with latest run
            # Compare datetime to determine which is the latest
            # This ensures UI always shows the most recent test execution data for each day
            test_datetime_str = test.get('datetime', test.get('date', ''))
            existing_datetime_str = existing.get('datetime', existing.get('date', ''))
            
            # Normalize datetime strings (remove " to " if present)
            if test_datetime_str and ' to ' in test_datetime_str:
                test_datetime_str = test_datetime_str.split(' to ')[0].strip()
            if existing_datetime_str and ' to ' in existing_datetime_str:
                existing_datetime_str = existing_datetime_str.split(' to ')[0].strip()
            
            is_newer = False
            try:
                # Parse datetimes to compare
                if test_datetime_str and existing_datetime_str:
                    try:
                        test_dt = datetime.fromisoformat(test_datetime_str.replace('Z', '+00:00') if 'Z' in test_datetime_str else test_datetime_str)
                        existing_dt = datetime.fromisoformat(existing_datetime_str.replace('Z', '+00:00') if 'Z' in existing_datetime_str else existing_datetime_str)
                        is_newer = test_dt > existing_dt
                    except:
                        # If parsing fails, compare as strings
                        is_newer = test_datetime_str > existing_datetime_str
                elif test_datetime_str:
                    # New entry has datetime, existing doesn't - consider it newer
                    is_newer = True
                else:
                    # Neither has datetime, keep existing (don't replace)
                    is_newer = False
            except Exception as e:
                print(f"Warning: Could not compare datetimes for {test_name}: {e}, keeping existing entry")
                is_newer = False
            
            # SPECIAL CASE: For db_solr_sync test, ALWAYS replace same-day entry with latest run
            if 'db_solr_sync' in test_name.lower():
                # CRITICAL: For db_solr_sync, check JSON file FIRST to get actual failure data
                # This ensures we always use the most accurate data from JSON
                json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
                # CRITICAL: Preserve datetime - use existing datetime, test datetime, or JSON file time (in priority order)
                stable_datetime = existing.get('datetime', '') or test.get('datetime', '')
                # Normalize datetime format - if it has " to ", extract just the start time
                if stable_datetime and ' to ' in stable_datetime:
                    stable_datetime = stable_datetime.split(' to ')[0].strip()
                
                # Read JSON file to get actual failure count and update test status
                if json_failure_path.exists():
                    try:
                        with open(json_failure_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        total_failures = json_data.get('total_failures', 0)
                        total_jobs = json_data.get('total_jobs_checked', json_data.get('total_jobs_available', 0))
                        
                        # CRITICAL: Always update total_jobs and error_jobs_count from JSON (even if test passed)
                        test['error_jobs_count'] = total_failures
                        test['total_jobs'] = total_jobs
                        
                        # CRITICAL: If JSON shows failures, force update test status to FAIL
                        if total_failures > 0:
                            test['status'] = 'FAIL'
                            # Read failure details from JSON
                            failures_list = json_data.get('failures', [])
                            test['error_jobs'] = [
                                {
                                    'id': str(f.get('id', 'N/A')),
                                    'title': str(f.get('db_title', 'N/A'))[:100],
                                    'error': str(f.get('msg', 'N/A'))[:500]
                                }
                                for f in failures_list[:total_failures]
                            ]
                            # Build failure message
                            structured_msg = "=" * 120 + "\n"
                            structured_msg += "SOLR SYNC FAILURE SUMMARY\n"
                            structured_msg += "=" * 120 + "\n"
                            if total_jobs > 0:
                                structured_msg += f"Total Jobs Available in DB (last 24h): {total_jobs}\n"
                            structured_msg += f"Jobs Actually Checked: {total_jobs}\n"
                            structured_msg += f"Total Failures: {total_failures}\n"
                            if total_failures > 0 and total_jobs > 0:
                                success_rate = ((total_jobs - total_failures) / total_jobs * 100) if total_jobs > 0 else 0
                                structured_msg += f"Success Rate: {success_rate:.2f}%\n"
                            structured_msg += "=" * 120 + "\n"
                            structured_msg += f"\n📄 Complete failure details saved in: reports/db_solr_sync_failures.json\n"
                            test['failure_message'] = structured_msg[:2000]
                            test['error_details'] = structured_msg[:2000]
                        else:
                            # Even when test passes, ensure error_jobs is an empty array (not missing)
                            test['error_jobs'] = []
                        
                        file_mtime = datetime.fromtimestamp(json_failure_path.stat().st_mtime)
                        # Use JSON file time as stable source - this is when test actually completed
                        # But only if we don't already have a datetime (preserve existing if available)
                        if not stable_datetime:
                            stable_datetime = file_mtime.isoformat()
                        else:
                            # Prefer JSON file time as it's more accurate, but keep existing if JSON time is older
                            try:
                                existing_dt = datetime.fromisoformat(stable_datetime.replace('Z', '+00:00') if 'Z' in stable_datetime else stable_datetime.split(' to ')[0])
                                if file_mtime > existing_dt:
                                    stable_datetime = file_mtime.isoformat()
                            except:
                                # If parsing fails, use JSON file time
                                stable_datetime = file_mtime.isoformat()
                    except Exception as e:
                        print(f"Warning: Could not read JSON file for db_solr_sync: {e}")
                else:
                    # JSON file doesn't exist - use test datetime if available, otherwise keep existing
                    if not stable_datetime:
                        stable_datetime = test.get('datetime', '')
                    # If still no datetime, use current time as last resort
                    if not stable_datetime:
                        stable_datetime = datetime.now().isoformat()
                
                # Always update - replace entire entry with new data
                history[test_name].remove(existing)
                # CRITICAL: Delete ALL old entries for db_solr_sync - keep only latest
                # This ensures only new/updated data is shown, old data is completely removed
                history[test_name] = []  # Clear all old entries AGAIN (double safety)
                # Will add new entry below
                existing = None
                # Store stable datetime for use in new entry
                test['stable_datetime'] = stable_datetime
            else:
                # CRITICAL: For ALL tests, ALWAYS replace same-day entry with latest run
                # Compare datetime to determine which is newer - always keep the latest
                should_update = is_newer  # Use the comparison we did above
                
                # If datetime comparison didn't work, check other indicators
                if not should_update:
                    # Check if new test has more recent information
                    if test.get('datetime') and not existing.get('datetime'):
                        should_update = True
                    elif test.get('start_time') and existing.get('start_time'):
                        # Compare start times if available
                        try:
                            # Format: YYYYMMDD HH:MM:SS
                            new_start = test['start_time']
                            existing_start = existing['start_time']
                            if new_start > existing_start:
                                should_update = True
                        except:
                            pass
                
                # CRITICAL: Always update if new run is detected (same day, multiple runs)
                # This ensures we always show the latest run for each day
                if should_update:
                    # Remove old entry and add new one
                    history[test_name].remove(existing)
                    existing = None
                else:
                    # New entry is not newer, keep existing
                    continue  # Skip adding this test entry
                
                # Entry already removed above if should_update is True, so we'll add new entry below
        
        if not existing:
            # CRITICAL: Only store test runs that have failures (FAIL status with errors)
            # Skip PASS tests or tests with no errors to save space
            test_status = test.get('status', 'UNKNOWN')
            error_count = test.get('error_jobs_count', 0)
            error_jobs_list = test.get('error_jobs', [])
            
            # SPECIAL CASE: For db_solr_sync test, ALWAYS clear old entries before adding new
            # This ensures only latest data is shown, old data is completely removed
            if 'db_solr_sync' in test_name.lower():
                # CRITICAL: Clear ALL old entries before adding new one
                history[test_name] = []
                print(f"CLEANED: Cleared all old entries for {test_name} before adding new data")
            
            # Only add to history if:
            # 1. Test status is FAIL, OR
            # 2. There are actual errors (error_count > 0 or error_jobs_list has items)
            # SPECIAL CASE: For db_solr_sync test, store both PASS and FAIL cases
            # Store PASS cases to preserve datetime for UI display, FAIL cases with full error details
            if 'db_solr_sync' in test_name.lower():
                # CRITICAL: Use stable datetime (from JSON file) if available, otherwise use test datetime
                entry_datetime = test.get('stable_datetime') or test.get('datetime', '')
                
                # Normalize datetime format - if it has " to ", extract just the start time
                if entry_datetime and ' to ' in entry_datetime:
                    entry_datetime = entry_datetime.split(' to ')[0].strip()
                
                # If no datetime, try to get from JSON file (most stable source)
                if not entry_datetime and 'db_solr_sync' in test_name.lower():
                        json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
                        if json_failure_path.exists():
                            try:
                                file_mtime = datetime.fromtimestamp(json_failure_path.stat().st_mtime)
                                entry_datetime = file_mtime.isoformat()
                            except:
                                pass
                    
                # If still no datetime, use test datetime or current time as fallback
                if not entry_datetime:
                    test_datetime = test.get('datetime', '')
                    # Normalize test datetime too if it has " to "
                    if test_datetime and ' to ' in test_datetime:
                        test_datetime = test_datetime.split(' to ')[0].strip()
                    entry_datetime = test_datetime
                if not entry_datetime:
                    entry_datetime = datetime.now().isoformat()
                
                # Store entry for both PASS and FAIL cases to preserve datetime
                    new_entry = {
                        'test_name': test_name,
                        'status': test_status,
                        'date': test_date,
                        'datetime': entry_datetime,  # Use stable datetime
                        'start_time': test.get('start_time', ''),
                        'end_time': test.get('end_time', ''),
                        'running_time': test.get('running_time', 'N/A'),
                        'line_no': test.get('line_no', 0)
                    }
                
                # Add totals if available
                    if test.get('total_jobs'):
                        new_entry['total_jobs'] = test.get('total_jobs')
                
                # CRITICAL: Store error details if there are failures, regardless of test status
                # This ensures failures are shown even when test passes (e.g., ALLOW_SOLR_SYNC_FAILURES=1)
                    if error_count > 0:
                        new_entry['error_jobs_count'] = error_count
                    
                    # CRITICAL: Only store error_jobs (failures only, not all entities)
                    if error_jobs_list and len(error_jobs_list) > 0:
                        # Limit to error_count to ensure we only store actual failures
                        limited_error_jobs = error_jobs_list
                        if error_count > 0 and len(error_jobs_list) > error_count:
                            limited_error_jobs = error_jobs_list[:error_count]
                        
                        # Only store essential error data: id, title, error (failures only)
                        new_entry['error_jobs'] = [
                            {
                                'id': str(job.get('id', 'N/A')),
                                'title': str(job.get('title', 'N/A'))[:100],  # Limit title length
                                'error': str(job.get('error', 'N/A'))[:500]   # Limit error length
                            }
                            for job in limited_error_jobs
                        ]
                    else:
                        # If error_jobs_list is empty but error_count > 0, set empty array
                        new_entry['error_jobs'] = []
                    
                    # Only add failure_message if there are actual errors
                    if test.get('failure_message'):
                        new_entry['failure_message'] = test.get('failure_message', '')[:2000]  # Limit length
                    if test.get('error_details'):
                        new_entry['error_details'] = test.get('error_details', '')[:2000]  # Limit length
                else:
                    # For PASS cases with no errors, ensure error_jobs is empty array (not missing)
                    new_entry['error_jobs'] = []
                    new_entry['error_jobs_count'] = 0
                    
                # Store entry in history (both PASS and FAIL to preserve datetime)
                    # Note: history[test_name] was already cleared above for db_solr_sync
                    history[test_name].append(new_entry)
            else:
                # CRITICAL: For ALL tests, store BOTH PASS and FAIL cases
                # This ensures we have complete history for all test runs
                # Store the latest run per day (already handled above by replacing same-day entries)
                new_entry = {
                    'test_name': test_name,
                    'status': test_status,
                    'date': test_date,
                    'datetime': test.get('datetime', ''),
                    'start_time': test.get('start_time', ''),
                    'end_time': test.get('end_time', ''),
                    'running_time': test.get('running_time', 'N/A'),
                    'line_no': test.get('line_no', 0)
                }
                
                # Add totals and error jobs if available (only essential error data)
                if test.get('total_jobs'):
                    new_entry['total_jobs'] = test.get('total_jobs')
                if error_count > 0:
                    new_entry['error_jobs_count'] = error_count
                else:
                    new_entry['error_jobs_count'] = 0
                
                # CRITICAL: Only store error_jobs if there are actual failures (not empty list)
                if error_jobs_list and len(error_jobs_list) > 0:
                    limited_error_jobs = error_jobs_list
                    if error_count > 0 and len(error_jobs_list) > error_count:
                        limited_error_jobs = error_jobs_list[:error_count]
                    
                    new_entry['error_jobs'] = [
                        {
                            'id': str(job.get('id', 'N/A')),
                            'title': str(job.get('title', 'N/A'))[:100],
                            'error': str(job.get('error', 'N/A'))[:500]
                        }
                        for job in limited_error_jobs
                    ]
                else:
                    new_entry['error_jobs'] = []
                
                # Only add failure_message if there are actual errors
                if error_count > 0 and test.get('failure_message'):
                    new_entry['failure_message'] = test.get('failure_message', '')[:2000]
                if error_count > 0 and test.get('error_details'):
                    new_entry['error_details'] = test.get('error_details', '')[:2000]
                
                # Store entry for both PASS and FAIL cases
                history[test_name].append(new_entry)
    
    # Clean up: Remove any tests that don't belong to this module from history
    # For BenchSale modules, filter by pattern. For Employer/JobSeeker, filter by exclusion rules.
    tests_to_remove = []
    for test_name in history.keys():
        if module in ['benchsale_admin', 'benchsale_recruiter', 'benchsale_test']:
            # BenchSale: filter by pattern
            if not is_test_for_module(test_name, module):
                tests_to_remove.append(test_name)
        else:
            # Employer/JobSeeker: filter by exclusion (remove if clearly belongs to another module)
            if not is_test_for_module(test_name, module):
                tests_to_remove.append(test_name)
    
    for test_name in tests_to_remove:
        del history[test_name]
        print(f"Removed unrelated test '{test_name}' from {module} history")
    
    # CRITICAL: Clean up old data (keep only last 7 days) - Auto-delete for storage concern
    # This ensures storage doesn't grow indefinitely
    tests_deleted = _cleanup_old_data(history, module, save_changes=True)
    
    if tests_deleted > 0:
        print(f"Auto-deleted {tests_deleted} test records older than 7 days for {module} (storage cleanup)")
    
    # Validate history before saving - ensure we're not losing all data
    total_tests = len(history)
    total_entries = sum(len(entries) for entries in history.values())
    
    if total_tests == 0 and total_entries == 0:
        # Don't save empty history - might be a parsing error
        print(f"Warning: {module} history would be empty after update, keeping existing data")
        # Reload existing history to preserve it
        existing_history = load_historical_data(module)
        if existing_history:
            history = existing_history
            print(f"Preserved existing {module} history ({len(existing_history)} tests)")
    
    # Save updated history
    save_historical_data(module, history)


def get_7day_log_data(module: str, test_case: str, force_reload: bool = False) -> List[Dict]:
    """Get 7-day log data for a specific test case - ONLY if it belongs to the module
    force_reload: If True, force fresh read from disk (no caching)"""
    # CRITICAL: Verify test belongs to module (for ALL modules) - STRICT CHECK
    if not is_test_for_module(test_case, module):
        print(f"BLOCKED: '{test_case}' does not belong to {module} - returning empty data")
        return []  # Return empty if test doesn't belong to this module
    
    # CRITICAL: Force fresh read for db_solr_sync to ensure latest data
    if 'db_solr_sync' in test_case.lower():
        force_reload = True
    
    history = load_historical_data(module, force_reload=force_reload)
    
    # CRITICAL: For read-only operations, DON'T modify history file during reads
    # Only filter in memory - don't save changes
    # This prevents data loss when API is called multiple times
    # History file should only be modified by update_historical_data
    # Note: We still filter in memory to ensure correct data is returned, but don't save
    
    if test_case not in history:
        # Try a fast scan of the log tail for this specific test (non-blocking).
        fast_entries = _build_history_from_log_tail(module, test_case)
        if fast_entries:
            history[test_case] = fast_entries
            try:
                save_historical_data(module, history)
            except Exception as e:
                print(f"Warning: Could not save fast history for {module}/{test_case}: {e}")
        else:
            # Start background update without blocking the API.
            _start_update_if_needed(module)
            history = load_historical_data(module)
    
    # Final check: ensure test_case still belongs to module after update
    if not is_test_for_module(test_case, module):
        print(f"BLOCKED: '{test_case}' does not belong to {module} after update - returning empty data")
        return []
    
    test_history = history.get(test_case, [])
    
    # CRITICAL: Ensure all entries have proper 'date' field extracted from datetime if missing
    # This fixes cases where entries were stored without explicit date field
    for entry in test_history:
        if 'date' not in entry or not entry.get('date'):
            # Extract date from datetime field
            dt_str = entry.get('datetime', '')
            if dt_str:
                # Handle ISO format: "2026-01-29T12:56:34" -> "2026-01-29"
                if 'T' in dt_str:
                    entry['date'] = dt_str.split('T')[0]
                elif ' ' in dt_str:
                    entry['date'] = dt_str.split(' ')[0]
                else:
                    # Try to parse as datetime and extract date
                    try:
                        # Use datetime from module-level import (not local import)
                        if 'Z' in dt_str or '+' in dt_str:
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromisoformat(dt_str)
                        entry['date'] = dt.strftime('%Y-%m-%d')
                    except:
                        # Fallback: use today's date
                        entry['date'] = datetime.now().strftime('%Y-%m-%d')
            else:
                # No datetime either, use today's date as fallback
                entry['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # SPECIAL CASE: For db_solr_sync test, UI should always show ONLY latest run
    # (not full 7-day history). This makes it easy to see current failure data
    # every time the test is executed.
    if 'db_solr_sync' in test_case.lower():
        if not test_history:
            return []
        
        # CRITICAL: For db_solr_sync, keep only the latest entry in history
        # Sort by datetime (fallback to date) and return the most recent entry only
        def _sort_key(entry: Dict) -> str:
            dt = entry.get('datetime') or entry.get('date', '')
            return dt
        
        sorted_history = sorted(test_history, key=_sort_key, reverse=True)
        latest = sorted_history[0]

        # CRITICAL: Normalize datetime format - extract just start time if it has " to "
        if isinstance(latest, dict) and latest.get('datetime'):
            datetime_str = latest['datetime']
            if ' to ' in datetime_str:
                latest['datetime'] = datetime_str.split(' to ')[0].strip()

        # CRITICAL: De-duplicate error_jobs to avoid duplicate rows in UI/API
        if isinstance(latest, dict) and latest.get('error_jobs'):
            deduped_jobs = _dedupe_error_jobs(latest.get('error_jobs', []))
            latest['error_jobs'] = deduped_jobs
            # Ensure list doesn't exceed reported failure count
            reported_count = int(latest.get('error_jobs_count') or 0)
            if reported_count > 0 and len(latest['error_jobs']) > reported_count:
                latest['error_jobs'] = latest['error_jobs'][:reported_count]
            # Backfill detected_at for entries missing it
            detected_at = latest.get('stable_datetime') or latest.get('datetime') or latest.get('date')
            for item in latest['error_jobs']:
                if isinstance(item, dict) and 'detected_at' not in item:
                    item['detected_at'] = detected_at
        
        # CRITICAL: For read-only operations, DON'T modify history file
        # Only return the latest entry without saving - this prevents data loss
        # History file should only be modified by update_historical_data, not by get_7day_log_data
        # This ensures data persists across API calls and refreshes
        
        # Return the latest entry (already sorted and processed above)
        return [latest]
    
    # Default behaviour for all other tests: 7‑day history
    today = datetime.now()
    result = []
    
    for i in range(7):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        # Find entry for this date - check both 'date' field and extract date from 'datetime'
        entry = None
        for t in test_history:
            # Check direct date match
            if t.get('date') == date:
                entry = t
                break
            # Also check if datetime starts with this date (handles ISO format)
            # CRITICAL: Handle " to " format by extracting just the start date
            dt_str = t.get('datetime', '')
            if dt_str:
                # Extract start date if " to " is present
                if ' to ' in dt_str:
                    dt_str = dt_str.split(' to ')[0].strip()
                # Check if datetime starts with this date
                if dt_str.startswith(date):
                    entry = t
                    break
        
        if entry:
            # Ensure date field is set correctly
            if 'date' not in entry or entry.get('date') != date:
                entry = entry.copy()  # Don't modify original
                entry['date'] = date
            result.append(entry)
        else:
            # Add placeholder for missing date
            result.append({
                'test_name': test_case,
                'status': 'NOT_RUN',
                'date': date,
                'datetime': f"{date}T00:00:00",
                'start_time': '',
                'end_time': '',
                'running_time': 'N/A',
                'failure_message': '',
                'error_details': ''
            })
    
    return result


# API Endpoints

@app.route('/api/modules', methods=['GET'])
def get_modules():
    """Get list of all modules"""
    return jsonify([
        {
            'id': module_id,
            'name': config['name'],
            'log_file': config['log_file']
        }
        for module_id, config in MODULES.items()
    ])


@app.route('/api/modules/<module_id>/test-cases', methods=['GET'])
def get_test_cases(module_id: str):
    """Get list of test cases for a module - STRICT FILTERING to ensure data isolation"""
    if module_id not in MODULES:
        return jsonify({'error': 'Module not found'}), 404
    
    # Start background update only if needed (avoid heavy re-parsing on every request)
    _start_update_if_needed(module_id)
    
    # Get all test cases and filter strictly (uses existing history data)
    all_test_cases = get_all_test_cases(module_id)
    
    # CRITICAL: Double-check filtering - remove any tests that don't belong
    filtered_test_cases = []
    for test_case in all_test_cases:
        if is_test_for_module(test_case, module_id):
            filtered_test_cases.append(test_case)
        else:
            print(f"API FILTER: Removed '{test_case}' from {module_id} test cases (doesn't belong)")
    
    return jsonify(filtered_test_cases)


@app.route('/api/modules/<module_id>/test-cases/<path:test_case>/history', methods=['GET'])
def get_test_history(module_id: str, test_case: str):
    """Get 7-day history for a specific test case - STRICT FILTERING to ensure data isolation"""
    try:
        if module_id not in MODULES:
            return jsonify({'error': 'Module not found'}), 404

        # Decode test case name (handle URL encoding)
        test_case = test_case.replace('%20', ' ').replace('%3A', ':')

        # CRITICAL: Verify test belongs to module BEFORE processing
        if not is_test_for_module(test_case, module_id):
            print(f"API BLOCK: '{test_case}' does not belong to {module_id} - returning empty history")
            return jsonify([])  # Return empty array if test doesn't belong

        def _response(data):
            response = jsonify(data)
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        # Fast path for db_solr_sync using JSON file if available
        if 'db_solr_sync' in test_case.lower():
            try:
                project_root = get_project_root()
                json_failure_path = project_root / "reports" / "db_solr_sync_failures.json"
                print(f"API-DB-SOLR-SYNC: Fast JSON path for {test_case}")
                print(f"API-JSON-CHECK: JSON file exists: {json_failure_path.exists()}, path: {json_failure_path}")

                if json_failure_path.exists():
                    import json
                    from datetime import datetime

                    with open(json_failure_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)

                    total_failures = json_data.get('total_failures', 0)
                    total_jobs = json_data.get('total_jobs_checked', json_data.get('total_jobs_available', 0))
                    file_mtime = datetime.fromtimestamp(json_failure_path.stat().st_mtime)
                    stable_datetime = file_mtime.isoformat()
                    if ' to ' in stable_datetime:
                        stable_datetime = stable_datetime.split(' to ')[0].strip()

                    entry = {
                        'test_name': test_case,
                        'status': 'FAIL' if total_failures > 0 else 'PASS',
                        'date': file_mtime.strftime('%Y-%m-%d'),
                        'datetime': stable_datetime,
                        'stable_datetime': stable_datetime,
                        'total_jobs': total_jobs,
                        'error_jobs_count': total_failures,
                        'running_time': 'N/A',
                        'start_time': file_mtime.strftime('%Y%m%d %H:%M:%S'),
                        'end_time': '',
                        'line_no': 0,
                        'error_jobs': []
                    }

                    if total_failures > 0:
                        failures_list = json_data.get('failures', [])
                        entry['error_jobs'] = [
                            {
                                'id': str(f.get('id', 'N/A')),
                                'title': str(f.get('db_title', 'N/A'))[:100],
                                'error': str(f.get('msg', 'N/A'))[:500],
                                'detected_at': stable_datetime
                            }
                            for f in failures_list[:total_failures]
                        ]
                        entry['error_jobs'] = _dedupe_error_jobs(entry['error_jobs'])
                        if len(entry['error_jobs']) > total_failures:
                            entry['error_jobs'] = entry['error_jobs'][:total_failures]
                        entry['failure_message'] = (
                            f"Solr Sync Failed for {total_failures}/{total_jobs} jobs checked "
                            f"(all jobs from last 24 hours). See logs for details."
                        )

                    history = load_historical_data(module_id, force_reload=False)
                    history[test_case] = [entry]
                    try:
                        save_historical_data(module_id, history)
                    except Exception as save_err:
                        print(f"API-SAVE-ERROR: Failed to save history for {test_case}: {save_err}")

                    return _response([entry])
            except Exception as e:
                print(f"API-UPDATE-ERROR: Failed to update {test_case} from JSON: {e}")

        # For non-db_solr_sync tests, avoid heavy updates inside request handlers
        if 'db_solr_sync' not in test_case.lower():
            log_data = get_7day_log_data(module_id, test_case, force_reload=False)
        else:
            # For db_solr_sync, fallback to history/log parsing if JSON path didn't return
            log_data = get_7day_log_data(module_id, test_case, force_reload=True)

        # Final verification: ensure all returned data is for this test case and module
        # Note: get_7day_log_data already filters by test_case, so all entries should match
        filtered_data = []
        for entry in log_data:
            entry_test_name = entry.get('test_name', '')
            # For NOT_RUN entries, test_name might be set correctly but we still want to include them
            # Only filter out if test_name doesn't match AND it's not a NOT_RUN placeholder
            if entry.get('status') == 'NOT_RUN' or entry_test_name == test_case:
                if entry.get('datetime') and ' to ' in entry['datetime']:
                    entry['datetime'] = entry['datetime'].split(' to ')[0].strip()
                # Ensure test_name is set correctly for all entries
                if 'test_name' not in entry or entry.get('test_name') != test_case:
                    entry['test_name'] = test_case
                filtered_data.append(entry)
            elif entry_test_name and is_test_for_module(entry_test_name, module_id):
                # Entry has different test_name but belongs to module - include it
                if entry.get('datetime') and ' to ' in entry['datetime']:
                    entry['datetime'] = entry['datetime'].split(' to ')[0].strip()
                filtered_data.append(entry)
            else:
                print(f"API FILTER: Removed entry for '{entry_test_name}' from {module_id} history (doesn't match {test_case})")
        
        return _response(filtered_data)
    except Exception as e:
        print(f"API-ERROR: Error in get_test_history for {module_id}/{test_case}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 200


@app.route('/api/modules/<module_id>/download-log', methods=['GET'])
def download_log(module_id: str):
    """Download log file for a module"""
    if module_id not in MODULES:
        return jsonify({'error': 'Module not found'}), 404
    
    project_root = get_project_root()
    log_file_path = project_root / MODULES[module_id]['log_file']
    
    if not log_file_path.exists():
        return jsonify({'error': 'Log file not found'}), 404
    
    return send_file(
        str(log_file_path),
        as_attachment=True,
        download_name=f"{module_id}_{datetime.now().strftime('%Y%m%d')}.log"
    )


@app.route('/api/modules/<module_id>/update', methods=['POST'])
def update_module_data(module_id: str):
    """Manually trigger update of historical data for a module"""
    if module_id not in MODULES:
        return jsonify({'error': 'Module not found'}), 404
    
    update_historical_data(module_id)
    return jsonify({'status': 'updated'})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running"""
    return jsonify({
        'status': 'running',
        'modules': list(MODULES.keys()),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/update-all', methods=['POST'])
def update_all_modules():
    """Update historical data for all modules"""
    results = {}
    for module_id in MODULES.keys():
        try:
            update_historical_data(module_id)
            results[module_id] = 'updated'
        except Exception as e:
            results[module_id] = f'error: {str(e)}'
    return jsonify(results)


def migrate_old_benchsale_data():
    """Migrate old benchsale_history.json to separate admin and recruiter files"""
    old_file = HISTORY_DIR / 'benchsale_history.json'
    if old_file.exists():
        try:
            with open(old_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            # Try to split data based on test names or create separate files
            admin_data = {}
            recruiter_data = {}
            
            for test_name, test_history in old_data.items():
                # Check if test name suggests admin or recruiter
                test_lower = test_name.lower()
                if 'admin' in test_lower or 't1' in test_lower:
                    admin_data[test_name] = test_history
                elif 'recruiter' in test_lower or 't2' in test_lower:
                    recruiter_data[test_name] = test_history
                else:
                    # Default to admin if unclear
                    admin_data[test_name] = test_history
            
            # Save separate files
            if admin_data:
                save_historical_data('benchsale_admin', admin_data)
            if recruiter_data:
                save_historical_data('benchsale_recruiter', recruiter_data)
            
            # Backup old file
            old_file.rename(HISTORY_DIR / 'benchsale_history.json.backup')
            print("Migrated old benchsale data to separate admin and recruiter files")
        except Exception as e:
            print(f"Error migrating old benchsale data: {e}")


if __name__ == '__main__':
    # Migrate old data if exists
    migrate_old_benchsale_data()
    
    # Initialize history for all modules in background thread to avoid blocking server startup
    def init_history():
        """Initialize history in background"""
        for module_id in MODULES.keys():
            try:
                update_historical_data(module_id)
            except Exception as e:
                print(f"Error updating history for {module_id}: {e}")
    
    # Start history update in background
    history_thread = threading.Thread(target=init_history, daemon=True)
    history_thread.start()
    
    # Run with better error handling for 24/7 operation
    try:
        app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Server error: {e}")
        import traceback
        traceback.print_exc()
        raise
