"""
Helper script to add test to queue file.
Called from dashboard when HTTP server is not available.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
QUEUE_FILE = PROJECT_ROOT / '.test_queue.json'


def add_test_to_queue(test_name):
    """Add test name to queue file."""
    try:
        # Read existing queue
        if QUEUE_FILE.exists():
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                queue = data.get('queue', [])
        else:
            queue = []
        
        # Add test if not already in queue
        if test_name not in queue:
            queue.append(test_name)
        
        # Write queue back
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'queue': queue,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"Added test '{test_name}' to queue")
        return True
    except Exception as e:
        print(f"Error adding test to queue: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python queue_test.py <test_name>")
        sys.exit(1)
    
    test_name = sys.argv[1]
    if add_test_to_queue(test_name):
        sys.exit(0)
    else:
        sys.exit(1)
