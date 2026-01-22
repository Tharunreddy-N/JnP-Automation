"""
Force process the test queue - useful for debugging
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from utils.always_on_server import read_queue, process_queue, remove_lock, is_locked

if __name__ == '__main__':
    print("=" * 60)
    print("Force Processing Test Queue")
    print("=" * 60)
    print()
    
    # Check if locked
    if is_locked():
        print("Queue is locked. Removing lock...")
        remove_lock()
        print("Lock removed.")
        print()
    
    # Read queue
    queue = read_queue()
    print(f"Current queue: {queue}")
    print(f"Queue size: {len(queue)}")
    print()
    
    if not queue:
        print("Queue is empty. Nothing to process.")
        sys.exit(0)
    
    print("Processing queue...")
    print()
    process_queue()
    
    # Check queue again
    queue_after = read_queue()
    print()
    print(f"Queue after processing: {queue_after}")
    print(f"Remaining: {len(queue_after)}")
    print()
    print("Done!")
