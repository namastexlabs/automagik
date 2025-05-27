#!/usr/bin/env python3
"""Script to inspect database structure."""

import sqlite3
import sys
import os
from rich.console import Console
from rich.table import Table

console = Console()

def check_database(db_path: str):
    """Check database structure."""
    if not os.path.exists(db_path):
        console.print(f"[red]Error: Database file does not exist: {db_path}[/red]")
        return

    try:
        console.print(f"[cyan]Checking database: {db_path}[/cyan]")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        if not tables:
            console.print("[yellow]No tables found in database.[/yellow]")
            conn.close()
            return

        # Create a table to display results
        table = Table(title=f"Database Tables in {os.path.basename(db_path)}")
        table.add_column("Table Name", style="cyan")
        table.add_column("Columns", style="green")
        table.add_column("Row Count", style="yellow")

        for table_name in tables:
            table_name = table_name[0]
            # Skip sqlite internal tables
            if table_name.startswith('sqlite_'):
                continue
                
            cursor.execute(f"PRAGMA table_info(`{table_name}`)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Count rows
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                row_count = cursor.fetchone()[0]
            except sqlite3.OperationalError as e:
                console.print(f"[red]Error counting rows in {table_name}: {e}[/red]")
                row_count = "Error"

            table.add_row(table_name, ", ".join(column_names), str(row_count))

        console.print(table)

        conn.close()
    except Exception as e:
        console.print(f"[red]Error checking database {db_path}: {str(e)}[/red]")
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    # Paths to check
    possible_paths = [
        "scripts/solid_stan/product_folder_matcher/product_folder_matches.db",
        "scripts/solid_stan/drive_catalog.db"
    ]

    found_dbs = False
    if len(sys.argv) > 1:
        # Check specific path provided by user
        db_path = sys.argv[1]
        if os.path.exists(db_path):
            check_database(db_path)
            found_dbs = True
        else:
             console.print(f"[red]Provided database path does not exist: {db_path}[/red]")
    else:
        # Check default paths
        for path in possible_paths:
            if os.path.exists(path):
                check_database(path)
                print()  # Add a blank line between database outputs
                found_dbs = True

    if not found_dbs:
         console.print("[yellow]No database files found at expected locations:[/yellow]")
         for path in possible_paths:
             console.print(f"- {path}") 