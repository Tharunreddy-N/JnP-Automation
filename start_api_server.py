#!/usr/bin/env python
"""Start API server with proper error handling"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from utils.log_history_api import app
    print("=" * 80)
    print("Starting Log History API Server on http://127.0.0.1:5001")
    print("=" * 80)
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    
    app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)
except KeyboardInterrupt:
    print("\n[INFO] Server stopped by user")
except Exception as e:
    print(f"\n[ERROR] Server error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
