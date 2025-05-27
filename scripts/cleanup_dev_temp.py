#!/usr/bin/env python3
"""
Auto-cleanup script for dev/temp directory.

This script removes files older than 30 days from the dev/temp directory
to prevent accumulation of temporary development scripts.

Usage:
    python scripts/cleanup_dev_temp.py [--dry-run] [--days N]
    
Options:
    --dry-run    Show what would be deleted without actually deleting
    --days N     Set custom retention period (default: 30 days)
    --verbose    Show detailed information about cleanup process
"""

import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def find_old_files(directory: Path, days: int) -> List[Tuple[Path, datetime]]:
    """
    Find files older than specified number of days.
    
    Args:
        directory: Directory to scan
        days: Number of days for retention
        
    Returns:
        List of (file_path, modification_time) tuples for old files
    """
    if not directory.exists():
        logging.info(f"Directory {directory} does not exist, skipping cleanup")
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    old_files = []
    
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.name != 'README.md':
            try:
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mod_time < cutoff_date:
                    old_files.append((file_path, mod_time))
            except (OSError, ValueError) as e:
                logging.warning(f"Error checking {file_path}: {e}")
    
    return old_files

def cleanup_files(files: List[Tuple[Path, datetime]], dry_run: bool = False) -> Tuple[int, int]:
    """
    Clean up the specified files.
    
    Args:
        files: List of (file_path, modification_time) tuples
        dry_run: If True, only show what would be deleted
        
    Returns:
        Tuple of (successful_deletions, failed_deletions)
    """
    successful = 0
    failed = 0
    
    for file_path, mod_time in files:
        try:
            if dry_run:
                print(f"[DRY RUN] Would delete: {file_path} (modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
                successful += 1
            else:
                file_path.unlink()
                logging.info(f"Deleted: {file_path}")
                successful += 1
        except OSError as e:
            logging.error(f"Failed to delete {file_path}: {e}")
            failed += 1
    
    return successful, failed

def cleanup_empty_directories(directory: Path, dry_run: bool = False) -> None:
    """Remove empty directories (except for README.md-only directories)."""
    for dir_path in directory.rglob('*'):
        if dir_path.is_dir() and dir_path != directory:
            try:
                # Check if directory is empty or contains only README.md
                contents = list(dir_path.iterdir())
                if not contents or (len(contents) == 1 and contents[0].name == 'README.md'):
                    if dry_run:
                        if not contents:
                            print(f"[DRY RUN] Would remove empty directory: {dir_path}")
                    else:
                        if not contents:
                            dir_path.rmdir()
                            logging.info(f"Removed empty directory: {dir_path}")
            except OSError as e:
                logging.warning(f"Could not remove directory {dir_path}: {e}")

def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(
        description="Clean up old files from dev/temp directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--days', 
        type=int, 
        default=30,
        help='Retention period in days (default: 30)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Show detailed information'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Find the dev/temp directory relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    temp_dir = project_root / 'dev' / 'temp'
    
    print(f"🧹 Cleaning up dev/temp directory: {temp_dir}")
    print(f"📅 Retention period: {args.days} days")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted")
    
    # Find old files
    old_files = find_old_files(temp_dir, args.days)
    
    if not old_files:
        print("✅ No files to clean up")
        return 0
    
    print(f"🗑️  Found {len(old_files)} files to clean up:")
    
    # Clean up files
    successful, failed = cleanup_files(old_files, args.dry_run)
    
    # Clean up empty directories
    if not args.dry_run:
        cleanup_empty_directories(temp_dir, args.dry_run)
    
    # Summary
    print("\n📊 Cleanup Summary:")
    print(f"   Files processed: {len(old_files)}")
    print(f"   Successfully {'would be ' if args.dry_run else ''}deleted: {successful}")
    if failed > 0:
        print(f"   Failed: {failed}")
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to actually delete files")
    
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    sys.exit(main()) 