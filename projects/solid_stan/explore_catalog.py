#!/usr/bin/env python3
import sqlite3
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint

# Initialize rich console
console = Console()

class DriveCatalogExplorer:
    def __init__(self, db_path: str = "drive_product_catalog.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        """Connect to the database."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        console.print(f"[green]Connected to database: {self.db_path}[/green]")

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            console.print("[yellow]Database connection closed[/yellow]")

    def get_table_info(self) -> Dict[str, List[str]]:
        """Get information about all tables in the database."""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = self.cursor.fetchall()
        
        table_info = {}
        for (table_name,) in tables:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in self.cursor.fetchall()]
            table_info[table_name] = columns
            
        return table_info

    def show_database_stats(self):
        """Display overall database statistics."""
        stats = {}
        
        # Get counts for each table
        for table in self.get_table_info().keys():
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = self.cursor.fetchone()[0]
        
        # Create stats table
        table = Table(title="Database Statistics")
        table.add_column("Table", style="cyan")
        table.add_column("Count", style="green")
        
        for table_name, count in stats.items():
            table.add_row(table_name, str(count))
            
        console.print(table)

    def explore_hierarchy(self):
        """Explore the folder hierarchy structure."""
        # Get hierarchy levels
        self.cursor.execute("""
            SELECT DISTINCT level, level_name 
            FROM drive_hierarchy 
            ORDER BY level
        """)
        levels = self.cursor.fetchall()
        
        # Create hierarchy table
        table = Table(title="Drive Hierarchy Structure")
        table.add_column("Level", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Count", style="yellow")
        
        for level, level_name in levels:
            self.cursor.execute("""
                SELECT COUNT(*) 
                FROM drive_hierarchy 
                WHERE level = ? AND level_name = ?
            """, (level, level_name))
            count = self.cursor.fetchone()[0]
            table.add_row(str(level), level_name, str(count))
            
        console.print(table)

    def search_by_name(self, search_term: str):
        """Search for items by name."""
        self.cursor.execute("""
            SELECT 
                di.name,
                di.item_type,
                di.full_path,
                di.web_view_link,
                dh.level_name
            FROM drive_items di
            JOIN drive_hierarchy dh ON di.id = dh.item_id
            WHERE di.name LIKE ?
            ORDER BY dh.level
        """, (f"%{search_term}%",))
        
        results = self.cursor.fetchall()
        
        if not results:
            console.print(f"[yellow]No results found for '{search_term}'[/yellow]")
            return
            
        table = Table(title=f"Search Results for '{search_term}'")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Level", style="yellow")
        table.add_column("Path", style="blue")
        
        for name, item_type, path, link, level in results:
            table.add_row(name, item_type, level, path)
            
        console.print(table)

    def get_item_details(self, item_id: int):
        """Get detailed information about a specific item."""
        # Get basic item info
        self.cursor.execute("""
            SELECT 
                di.*,
                dh.level,
                dh.level_name
            FROM drive_items di
            JOIN drive_hierarchy dh ON di.id = dh.item_id
            WHERE di.id = ?
        """, (item_id,))
        
        item = self.cursor.fetchone()
        if not item:
            console.print(f"[red]Item with ID {item_id} not found[/red]")
            return
            
        # Get metadata
        self.cursor.execute("""
            SELECT key, value
            FROM drive_item_metadata
            WHERE item_id = ?
        """, (item_id,))
        metadata = dict(self.cursor.fetchall())
        
        # Create details table
        table = Table(title=f"Item Details - ID: {item_id}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        # Add basic info
        for i, col in enumerate(self.cursor.description):
            if col[0] != 'id':  # Skip the id column as it's in the title
                table.add_row(col[0], str(item[i]))
                
        # Add metadata
        if metadata:
            table.add_row("---", "---")
            for key, value in metadata.items():
                table.add_row(f"Metadata: {key}", value)
                
        console.print(table)

    def explore_by_type(self, item_type: str):
        """Explore items of a specific type."""
        self.cursor.execute("""
            SELECT 
                di.name,
                di.full_path,
                di.web_view_link,
                dh.level_name
            FROM drive_items di
            JOIN drive_hierarchy dh ON di.id = dh.item_id
            WHERE di.item_type = ?
            ORDER BY dh.level
        """, (item_type,))
        
        results = self.cursor.fetchall()
        
        if not results:
            console.print(f"[yellow]No items found of type '{item_type}'[/yellow]")
            return
            
        table = Table(title=f"Items of Type: {item_type}")
        table.add_column("Name", style="cyan")
        table.add_column("Level", style="yellow")
        table.add_column("Path", style="blue")
        
        for name, path, link, level in results:
            table.add_row(name, level, path)
            
        console.print(table)

    def get_item_children(self, item_id: int):
        """Get all children of a specific item."""
        self.cursor.execute("""
            SELECT 
                child.name,
                child.item_type,
                child.full_path,
                child.web_view_link,
                dh.level_name
            FROM drive_items parent
            JOIN drive_items child ON child.parent_drive_id = parent.drive_id
            JOIN drive_hierarchy dh ON child.id = dh.item_id
            WHERE parent.id = ?
            ORDER BY dh.level
        """, (item_id,))
        
        results = self.cursor.fetchall()
        
        if not results:
            console.print(f"[yellow]No children found for item ID {item_id}[/yellow]")
            return
            
        table = Table(title=f"Children of Item ID: {item_id}")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Level", style="yellow")
        table.add_column("Path", style="blue")
        
        for name, item_type, path, link, level in results:
            table.add_row(name, item_type, level, path)
            
        console.print(table)

def main():
    try:
        explorer = DriveCatalogExplorer()
        
        while True:
            console.print("\n[bold cyan]Drive Catalog Explorer[/bold cyan]")
            console.print("1. Show Database Statistics")
            console.print("2. Explore Hierarchy Structure")
            console.print("3. Search by Name")
            console.print("4. Get Item Details")
            console.print("5. Explore by Type")
            console.print("6. Get Item Children")
            console.print("7. Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6", "7"])
            
            if choice == "1":
                explorer.show_database_stats()
                
            elif choice == "2":
                explorer.explore_hierarchy()
                
            elif choice == "3":
                search_term = Prompt.ask("Enter search term")
                explorer.search_by_name(search_term)
                
            elif choice == "4":
                item_id = Prompt.ask("Enter item ID", default="1")
                try:
                    explorer.get_item_details(int(item_id))
                except ValueError:
                    console.print("[red]Invalid item ID[/red]")
                    
            elif choice == "5":
                # Get available types
                explorer.cursor.execute("SELECT DISTINCT item_type FROM drive_items")
                types = [row[0] for row in explorer.cursor.fetchall()]
                
                console.print("\nAvailable types:")
                for i, type_name in enumerate(types, 1):
                    console.print(f"{i}. {type_name}")
                    
                type_choice = Prompt.ask("Select type number", choices=[str(i) for i in range(1, len(types) + 1)])
                explorer.explore_by_type(types[int(type_choice) - 1])
                
            elif choice == "6":
                item_id = Prompt.ask("Enter parent item ID", default="1")
                try:
                    explorer.get_item_children(int(item_id))
                except ValueError:
                    console.print("[red]Invalid item ID[/red]")
                    
            elif choice == "7":
                if Confirm.ask("Are you sure you want to exit?"):
                    break
                    
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
    finally:
        if 'explorer' in locals():
            explorer.close()

if __name__ == "__main__":
    main() 