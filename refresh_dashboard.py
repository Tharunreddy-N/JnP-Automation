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
    print("Refreshing BenchSale Dashboard...")
    try:
        dashboard_path = generate_unified_dashboard()
        print(f"[OK] Dashboard refreshed: {dashboard_path}")
        print("You can now open the dashboard in your browser.")
    except Exception as e:
        print(f"[ERROR] Failed to refresh dashboard: {e}")
        sys.exit(1)
