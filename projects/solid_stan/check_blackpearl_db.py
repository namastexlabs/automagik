import psycopg2
from dotenv import load_dotenv
import os
from rich.console import Console
from rich.table import Table
import urllib.parse
import socket
import requests
import signal
import sys

console = Console()

# Handle keyboard interrupt (CTRL+C)
def signal_handler(sig, frame):
    console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def get_ip_info():
    # Get hostname
    hostname = socket.gethostname()
    
    # Get local IP
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "Could not determine local IP"
    
    # Get public IP with a short timeout
    try:
        public_ip = requests.get('https://api.ipify.org', timeout=2).text
    except:
        try:
            public_ip = requests.get('https://ifconfig.me', timeout=2).text
        except:
            public_ip = "Could not determine public IP"
    
    return hostname, local_ip, public_ip

def display_product_families(cursor):
    """Display all product families from the database."""
    try:
        # Get all product families
        cursor.execute("""
            SELECT id, codigo, "nomeFamilia"
            FROM catalogo_familiadeproduto
            ORDER BY "nomeFamilia"
        """)
        
        families = cursor.fetchall()
        
        if not families:
            console.print("\n[yellow]No product families found in the database.[/yellow]")
            return
            
        # Create a table for display
        table = Table(title="Product Families")
        table.add_column("ID", style="cyan")
        table.add_column("Code", style="green")
        table.add_column("Family Name", style="yellow")
        
        # Add rows to the table
        for family in families:
            table.add_row(
                str(family[0]),  # id
                str(family[1]),  # codigo
                family[2]        # nomeFamilia
            )
        
        console.print("\n[bold]Product Families:[/bold]")
        console.print(table)
        console.print(f"\n[green]Total product families: {len(families)}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error displaying product families:[/red] {str(e)}")

def main():
    try:
        # Load environment variables
        load_dotenv()
        
        console.print("[bold]Starting database check...[/bold]")
        
        # Display IP information with timeout protection
        try:
            hostname, local_ip, public_ip = get_ip_info()
            console.print("[bold blue]===== IP Information =====[/bold blue]")
            console.print(f"[green]Hostname:[/green] {hostname}")
            console.print(f"[green]Local IP:[/green] {local_ip}")
            console.print(f"[green]Public IP:[/green] {public_ip}")
            console.print("[bold blue]=========================[/bold blue]\n")
        except Exception:
            console.print("[yellow]Could not get IP information, continuing...[/yellow]")
        
        # Get database URI from environment
        db_uri = os.getenv('BLACKPEARL_DB_URI')
        
        if not db_uri:
            console.print("[red]Error: BLACKPEARL_DB_URI not found in environment variables[/red]")
            return

        # Parse the connection string
        result = urllib.parse.urlparse(db_uri)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        console.print(f"[blue]Attempting to connect to database {database} at {hostname}...[/blue]")
        
        # Connect to database with timeout
        conn = None
        cursor = None
        
        try:
            # Connect with a connect_timeout
            conn = psycopg2.connect(
                host=hostname,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10  # 10 seconds connection timeout
            )
            
            # Create a cursor
            cursor = conn.cursor()
            
            # Get database version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            console.print("\n[green]Connected to Blackpearl Database successfully![/green]")
            console.print(f"[blue]Database Version:[/blue] {version}")
            console.print(f"[blue]Database Host:[/blue] {hostname}")
            console.print(f"[blue]Database Name:[/blue] {database}")
            
            # Display product families
            display_product_families(cursor)
            
            # Get all tables in the database
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            
            if not tables:
                console.print("\n[yellow]No tables found in the public schema.[/yellow]")
                return
                
            console.print("\n[bold]Tables found:[/bold]")
            console.print("-" * 50)
            
            for table_row in tables:
                table_name = table_row[0]
                
                # Create a table for each table's columns
                table = Table(title=f"Table: {table_name}")
                table.add_column("Column Name", style="cyan")
                table.add_column("Data Type", style="green")
                table.add_column("Nullable", style="yellow")
                
                # Get columns for each table
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cursor.fetchall()
                
                for column in columns:
                    table.add_row(
                        column[0],  # column name
                        column[1],  # data type
                        column[2]   # is_nullable
                    )
                
                console.print(table)
                console.print()
            
        except Exception as e:
            console.print(f"[red]Error connecting to database:[/red] {str(e)}")
            if "password authentication failed" in str(e).lower():
                console.print("[yellow]Hint: Check if the database credentials in BLACKPEARL_DB_URI are correct[/yellow]")
            elif "could not connect to server" in str(e).lower():
                console.print("[yellow]Hint: Check if the database server is running and accessible[/yellow]")
            elif "operation timed out" in str(e).lower():
                console.print("[yellow]Hint: Database connection timed out. Server might be unreachable.[/yellow]")
            
        finally:
            # Always properly close connections
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
            console.print("[blue]Database inspection complete.[/blue]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    # Ensure a clean exit
    sys.exit(0) 