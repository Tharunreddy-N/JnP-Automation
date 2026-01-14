"""
Cleanup script to remove old/unwanted HTML and log files from the project.
Makes the folder structure more professional and less cluttered.
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Directories to clean
CLEANUP_DIRS = {
    "reports/failures": {
        "patterns": ["*.html", "*.url.txt", "*.png"],
        "keep_days": 1,  # Keep files from last 1 day only
        "keep_recent_count": 5,  # Keep only the 5 most recent files
        "description": "Failure reports"
    },
    "logs": {
        "patterns": ["*.log", "*.html"],
        "keep_days": 3,  # Keep logs from last 3 days
        "description": "Log files",
        "keep_files": ["benchsale_test.log", "benchsale_test.html", "index.html", "benchsale_admin.log", "benchsale_admin.html", "benchsale_recruiter.log", "benchsale_recruiter.html"]  # Always keep these
    }
}

# Files to remove from root (if they exist and are old)
ROOT_FILES_TO_CHECK = [
    "BHAVANA N.pdf",  # Test file, can be removed
]


def get_file_age_days(file_path: Path) -> float:
    """Get the age of a file in days."""
    try:
        mtime = os.path.getmtime(file_path)
        age_seconds = time.time() - mtime
        return age_seconds / (24 * 60 * 60)
    except Exception:
        return 999  # If can't determine age, consider it old


def should_keep_file(file_path: Path, keep_days: int, always_keep: list = None) -> bool:
    """Determine if a file should be kept based on age and name."""
    # Always keep specific files
    if always_keep:
        if file_path.name in always_keep:
            return True
    
    # Keep files newer than keep_days
    age_days = get_file_age_days(file_path)
    return age_days <= keep_days


def get_file_mtime(file_path: Path) -> float:
    """Get file modification time."""
    try:
        return os.path.getmtime(file_path)
    except Exception:
        return 0


def cleanup_directory(dir_path: Path, config: dict) -> dict:
    """Clean up files in a directory based on configuration."""
    stats = {
        "removed": 0,
        "kept": 0,
        "errors": 0,
        "files_removed": []
    }
    
    if not dir_path.exists():
        print(f"  Directory does not exist: {dir_path}")
        return stats
    
    keep_days = config.get("keep_days", 7)
    keep_recent_count = config.get("keep_recent_count", None)
    always_keep = config.get("keep_files", [])
    patterns = config.get("patterns", [])
    
    # Collect all files matching patterns
    files_to_check = []
    for pattern in patterns:
        files_to_check.extend(dir_path.glob(pattern))
    
    # Remove duplicates
    files_to_check = list(set(files_to_check))
    
    # If keep_recent_count is set, sort files by modification time and keep only the most recent ones
    if keep_recent_count and keep_recent_count > 0:
        # Separate always_keep files from others
        always_keep_files = [f for f in files_to_check if f.name in (always_keep or [])]
        other_files = [f for f in files_to_check if f.name not in (always_keep or [])]
        
        # Sort other files by modification time (newest first)
        other_files.sort(key=get_file_mtime, reverse=True)
        
        # Keep only the most recent ones
        files_to_keep = set(always_keep_files + other_files[:keep_recent_count])
        files_to_remove = [f for f in other_files if f not in files_to_keep]
        
        # Remove old files
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                stats["removed"] += 1
                stats["files_removed"].append(file_path.name)
            except Exception as e:
                stats["errors"] += 1
                print(f"    ERROR removing {file_path.name}: {e}")
        
        stats["kept"] = len(files_to_keep)
    else:
        # Original logic: keep based on age
        for file_path in files_to_check:
            try:
                if should_keep_file(file_path, keep_days, always_keep):
                    stats["kept"] += 1
                    continue
                
                # Remove the file
                file_path.unlink()
                stats["removed"] += 1
                stats["files_removed"].append(file_path.name)
                
            except Exception as e:
                stats["errors"] += 1
                print(f"    ERROR removing {file_path.name}: {e}")
    
    return stats


def cleanup_root_files() -> dict:
    """Clean up unwanted files from project root."""
    stats = {
        "removed": 0,
        "errors": 0,
        "files_removed": []
    }
    
    for filename in ROOT_FILES_TO_CHECK:
        file_path = PROJECT_ROOT / filename
        if file_path.exists():
            try:
                file_path.unlink()
                stats["removed"] += 1
                stats["files_removed"].append(filename)
            except Exception as e:
                stats["errors"] += 1
                print(f"  ERROR removing {filename}: {e}")
    
    return stats


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("Project Cleanup - Removing Old HTML and Log Files")
    print("=" * 60)
    print()
    
    total_removed = 0
    total_kept = 0
    total_errors = 0
    
    # Clean up directories
    for dir_name, config in CLEANUP_DIRS.items():
        dir_path = PROJECT_ROOT / dir_name
        description = config.get("description", dir_name)
        
        print(f"Cleaning {description} ({dir_name})...")
        stats = cleanup_directory(dir_path, config)
        
        total_removed += stats["removed"]
        total_kept += stats["kept"]
        total_errors += stats["errors"]
        
        if stats["removed"] > 0:
            print(f"  [OK] Removed {stats['removed']} old file(s)")
            if len(stats["files_removed"]) <= 10:
                for fname in stats["files_removed"][:10]:
                    print(f"    - {fname}")
            else:
                for fname in stats["files_removed"][:5]:
                    print(f"    - {fname}")
                print(f"    ... and {len(stats['files_removed']) - 5} more")
        else:
            print(f"  [OK] No old files to remove")
        
        if stats["kept"] > 0:
            print(f"  [OK] Kept {stats['kept']} recent file(s)")
        
        if stats["errors"] > 0:
            print(f"  [WARNING] {stats['errors']} error(s) encountered")
        
        print()
    
    # Clean up root files
    print("Cleaning project root...")
    root_stats = cleanup_root_files()
    total_removed += root_stats["removed"]
    total_errors += root_stats["errors"]
    
    if root_stats["removed"] > 0:
        print(f"  [OK] Removed {root_stats['removed']} file(s) from root")
        for fname in root_stats["files_removed"]:
            print(f"    - {fname}")
    else:
        print(f"  [OK] No unwanted files in root")
    print()
    
    # Summary
    print("=" * 60)
    print("Cleanup Summary:")
    print(f"  Total files removed: {total_removed}")
    print(f"  Total files kept: {total_kept}")
    print(f"  Total errors: {total_errors}")
    print("=" * 60)
    print()
    print("[OK] Project cleanup completed!")
    print("  Your folder structure is now cleaner and more professional.")


if __name__ == "__main__":
    main()
