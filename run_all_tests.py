"""
Sequential Test Runner - Runs Admin tests first, then Recruiter tests
Usage:
    python run_all_tests.py
"""

import subprocess
import sys
from pathlib import Path


def run_tests(test_path, test_type):
    """Run pytest for a specific test file"""
    print("\n" + "=" * 80)
    print(f"Running {test_type} Tests...")
    print("=" * 80)
    print(f"Test file: {test_path}")
    print("=" * 80 + "\n")
    
    try:
        # Run pytest with verbose output
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "-s"],
            cwd=Path(__file__).parent,
            check=False  # Don't fail if tests fail, just continue
        )
        
        print("\n" + "=" * 80)
        print(f"{test_type} Tests Completed")
        print(f"Exit code: {result.returncode}")
        print("=" * 80 + "\n")
        
        return result.returncode
    except Exception as e:
        print(f"\n[ERROR] Failed to run {test_type} tests: {e}\n")
        return 1


def main():
    """Main function to run tests sequentially"""
    project_root = Path(__file__).parent
    
    admin_test_file = project_root / "tests" / "benchsale" / "test_benchsale_admin_test_cases.py"
    recruiter_test_file = project_root / "tests" / "benchsale" / "test_benchsale_recruiter_test_cases.py"
    
    print("\n" + "=" * 80)
    print("BenchSale Sequential Test Runner")
    print("=" * 80)
    print("This script will run:")
    print("  1. Admin tests first")
    print("  2. Recruiter tests second")
    print("=" * 80 + "\n")
    
    # Verify test files exist
    if not admin_test_file.exists():
        print(f"[ERROR] Admin test file not found: {admin_test_file}")
        sys.exit(1)
    
    if not recruiter_test_file.exists():
        print(f"[ERROR] Recruiter test file not found: {recruiter_test_file}")
        sys.exit(1)
    
    # Run Admin tests first
    admin_exit_code = run_tests(admin_test_file, "Admin")
    
    # Wait a moment between test runs
    print("\nWaiting 3 seconds before starting Recruiter tests...\n")
    import time
    time.sleep(3)
    
    # Run Recruiter tests second
    recruiter_exit_code = run_tests(recruiter_test_file, "Recruiter")
    
    # Final summary
    print("\n" + "=" * 80)
    print("Test Execution Summary")
    print("=" * 80)
    print(f"Admin Tests:    {'PASSED' if admin_exit_code == 0 else 'FAILED'} (exit code: {admin_exit_code})")
    print(f"Recruiter Tests: {'PASSED' if recruiter_exit_code == 0 else 'FAILED'} (exit code: {recruiter_exit_code})")
    print("=" * 80)
    
    # Return combined exit code (0 if both passed, 1 if any failed)
    final_exit_code = 0 if (admin_exit_code == 0 and recruiter_exit_code == 0) else 1
    print(f"\nOverall Status: {'ALL TESTS PASSED' if final_exit_code == 0 else 'SOME TESTS FAILED'}")
    print("=" * 80 + "\n")
    
    return final_exit_code


if __name__ == "__main__":
    sys.exit(main())
