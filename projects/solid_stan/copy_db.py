#!/usr/bin/env python3
"""Script to copy SQLite database from one location to another."""

import sqlite3
import os
import sys
import argparse
import shutil
from rich.console import Console
from rich.progress import Progress

console = Console()

def copy_database(source_path: str, dest_path: str, force: bool = False):
    """Copy database from source to destination.
    
    Args:
        source_path: Path to source database
        dest_path: Path to destination database
        force: Whether to overwrite destination if it exists
    """
    # Check if source exists
    if not os.path.exists(source_path):
        console.print(f"[red]Error: Source database does not exist: {source_path}[/red]")
        return False
    
    # Check if destination exists
    if os.path.exists(dest_path) and not force:
        console.print(f"[yellow]Destination database already exists: {dest_path}[/yellow]")
        console.print("[yellow]Use --force to overwrite.[/yellow]")
        return False
    
    # Create destination directory if it doesn't exist
    dest_dir = os.path.dirname(dest_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    try:
        # Method 1: Simple file copy
        console.print(f"[cyan]Copying database from {source_path} to {dest_path}...[/cyan]")
        shutil.copy2(source_path, dest_path)
        console.print(f"[green]Database copied successfully![/green]")
        
        # Verify the copy
        console.print(f"[cyan]Verifying database...[/cyan]")
        source_conn = sqlite3.connect(source_path)
        source_cursor = source_conn.cursor()
        
        dest_conn = sqlite3.connect(dest_path)
        dest_cursor = dest_conn.cursor()
        
        # Get all tables from source
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        source_tables = [row[0] for row in source_cursor.fetchall()]
        
        # Get all tables from destination
        dest_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        dest_tables = [row[0] for row in dest_cursor.fetchall()]
        
        # Check if tables match
        if set(source_tables) != set(dest_tables):
            console.print(f"[red]Warning: Tables in destination do not match source.[/red]")
            console.print(f"[yellow]Source tables: {source_tables}[/yellow]")
            console.print(f"[yellow]Destination tables: {dest_tables}[/yellow]")
            return False
        
        # Compare row counts
        with Progress() as progress:
            task = progress.add_task("[cyan]Verifying tables...", total=len(source_tables))
            
            for table in source_tables:
                source_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                source_count = source_cursor.fetchone()[0]
                
                dest_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                dest_count = dest_cursor.fetchone()[0]
                
                if source_count != dest_count:
                    console.print(f"[red]Warning: Row count mismatch in table {table}.[/red]")
                    console.print(f"[yellow]Source: {source_count} rows[/yellow]")
                    console.print(f"[yellow]Destination: {dest_count} rows[/yellow]")
                
                progress.update(task, advance=1)
        
        source_conn.close()
        dest_conn.close()
        
        console.print(f"[green]Database verification complete![/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]Error copying database: {str(e)}[/red]")
        return False

def main():
    parser = argparse.ArgumentParser(description='Copy SQLite database from one location to another.')
    parser.add_argument('source', help='Path to source database')
    parser.add_argument('destination', help='Path to destination database')
    parser.add_argument('--force', action='store_true', help='Overwrite destination if it exists')
    
    args = parser.parse_args()
    
    copy_database(args.source, args.destination, args.force)

if __name__ == "__main__":
    main() 