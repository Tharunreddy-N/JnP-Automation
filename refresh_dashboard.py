"""
Quick script to refresh/regenerate the unified dashboard
Can be called manually or associated with HTML file
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.unified_log_viewer import generate_unified_dashboard

if __name__ == '__main__':
    import time
    print("Refreshing BenchSale Dashboard...")
    
    # Wait a moment to ensure log files are fully flushed to disk
    # This is critical for reading the latest test results (PASS/FAIL status)
    time.sleep(2.5)  # Increased to 2.5 seconds to ensure log files are fully written
    
    try:
        dashboard_path = generate_unified_dashboard()
        print(f"[OK] Dashboard refreshed: {dashboard_path}")
        print("You can now open the dashboard in your browser.")
        
        # Additional wait to ensure dashboard file is written to disk
        time.sleep(1)  # Increased to 1 second
    except Exception as e:
        print(f"[ERROR] Failed to refresh dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
