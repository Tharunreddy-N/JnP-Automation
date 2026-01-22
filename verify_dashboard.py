"""Quick script to verify dashboard can read test results"""
from utils.unified_log_viewer import parse_test_results_from_log
from pathlib import Path

logs_dir = Path('logs')
log_files = ['employer.log', 'jobseeker.log', 'benchsale_admin.log', 'benchsale_test.log']

print("=" * 60)
print("Verifying Dashboard Can Read Test Results")
print("=" * 60)

for log_file in log_files:
    log_path = logs_dir / log_file
    if log_path.exists():
        print(f"\nChecking {log_file}...")
        tests = parse_test_results_from_log(str(log_path))
        print(f"  Found {len(tests)} test results")
        if tests:
            for test in tests[-3:]:  # Show last 3
                print(f"    - {test['name']}: {test['status']}")
        else:
            print("  No test results found")
    else:
        print(f"\n{log_file} - File not found")

print("\n" + "=" * 60)
print("Verification Complete!")
print("=" * 60)
