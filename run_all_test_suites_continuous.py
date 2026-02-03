#!/usr/bin/env python3
"""
Continuous Test Runner - Runs ALL test suites sequentially
BenchSale Admin → BenchSale Recruiter → Employer → JobSeeker
"""
import subprocess
import sys
import os
from pathlib import Path

def run_test_suite(suite_name, test_path):
    """Run a test suite and return success status"""
    print("\n" + "="*80)
    print(f"Running {suite_name}...")
    print("="*80 + "\n")
    
    cmd = [
        sys.executable, "-m", "pytest", 
        test_path, 
        "-v", 
        "--tb=short",
        "--maxfail=0",
        "--continue-on-collection-errors"
    ]
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    return result.returncode == 0

def main():
    """Run all test suites"""
    print("\n")
    print("="*80)
    print("  CONTINUOUS TEST RUNNER - ALL TEST SUITES".center(80))
    print("="*80)
    print("  Running: BenchSale Admin -> BenchSale Recruiter -> Employer -> JobSeeker".center(80))
    print("="*80 + "\n")
    
    suites = [
        ("BENCHSALE ADMIN TESTS", "tests/benchsale/test_benchsale_admin_test_cases.py"),
        ("BENCHSALE RECRUITER TESTS", "tests/benchsale/test_benchsale_recruiter_test_cases.py"),
        ("EMPLOYER TESTS", "tests/employer/test_employer_test_cases.py"),
        ("JOBSEEKER TESTS", "tests/jobseeker/"),  # Run all test files in jobseeker directory
    ]
    
    results = {}
    
    for suite_name, test_path in suites:
        print(f"\n\n{'='*80}")
        print(f"EXECUTING: {suite_name}")
        print(f"{'='*80}\n")
        success = run_test_suite(suite_name, test_path)
        results[suite_name] = "PASSED" if success else "FAILED"
        
        # Small pause between suites to allow browser cleanup
        import time
        time.sleep(2)
    
    # Print summary
    print("\n\n" + "="*80)
    print("TEST EXECUTION SUMMARY".center(80))
    print("="*80)
    for suite_name, status in results.items():
        print(f"{suite_name:<50} {status}")
    print("="*80)
    
    # Refresh dashboard
    print("\nRefreshing dashboard...")
    try:
        from utils.unified_log_viewer import generate_unified_dashboard
        dashboard_path = generate_unified_dashboard()
        print(f"Dashboard refreshed: {dashboard_path}")
    except Exception as e:
        print(f"WARNING: Could not refresh dashboard: {e}")
    
    print("\nAll test suites completed!\n")

if __name__ == "__main__":
    main()
