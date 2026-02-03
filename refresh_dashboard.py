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
    import os
    print("Refreshing BenchSale Dashboard...")
    
    # Minimal wait - just enough for log flush (reduced from 2.5 to 0.3 seconds)
    time.sleep(0.3)
    
    try:
        dashboard_path = generate_unified_dashboard()
        print(f"[OK] Dashboard refreshed: {dashboard_path}")
        print("You can now open the dashboard in your browser.")
        
        # Force file system sync and update timestamp
        dashboard_file = Path(dashboard_path)
        if dashboard_file.exists():
            try:
                # Update file timestamp to force browser reload
                current_time = time.time()
                os.utime(dashboard_file, (current_time, current_time))
                print(f"[OK] Dashboard file timestamp updated: {dashboard_file}")
            except Exception as e:
                print(f"[WARNING] Could not update dashboard timestamp: {e}")
        
        # No additional wait needed - file is already written
    except Exception as e:
        print(f"[ERROR] Failed to refresh dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
