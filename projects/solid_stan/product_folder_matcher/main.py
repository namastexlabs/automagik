#!/usr/bin/env python3
"""Main script for product folder matcher."""

import os
import sys
import signal
import asyncio
import argparse
import time
from typing import Dict, List, Set
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.panel import Panel
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)

from scripts.solid_stan.product_folder_matcher.models import BlackpearlProduct, DriveFolder
from scripts.solid_stan.product_folder_matcher.database import (
    connect_sqlite_db, connect_postgres_db, 
    create_results_tables, create_progress_table,
    get_products_by_brand, get_folders_by_brand,
    save_match_result, get_processed_products, get_last_brand_product,
    save_progress, check_and_record_duplicates, generate_summary_report
)
from scripts.solid_stan.product_folder_matcher.agent import MatchingAgent
from scripts.solid_stan.product_folder_matcher.tools import ProductFolderMatcherTools
from scripts.solid_stan.product_folder_matcher.observability import setup_logging, log_progress, log_error

# Initialize console for rich output
console = Console()

# Handle keyboard interrupt (CTRL+C)
def signal_handler(sig, frame):
    console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Match products with Drive folders.')
    
    parser.add_argument(
        '--brand', 
        type=str,
        help='Process only this specific brand'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        default=0,
        help='Limit the number of products to process per brand (0 for no limit)'
    )
    
    parser.add_argument(
        '--confidence-threshold', 
        type=float, 
        default=0.8,
        help='Minimum confidence score to consider a match valid'
    )
    
    parser.add_argument(
        '--restart',
        action='store_true',
        help='Restart processing from the beginning, ignoring previous progress'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving matches to database'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='openai:gpt-4o',
        help='Model name to use for matching'
    )
    
    parser.add_argument(
        '--output-db',
        type=str,
        default='scripts/solid_stan/product_folder_matcher/product_folder_matches.db',
        help='SQLite database file to store results'
    )
    
    parser.add_argument(
        '--logfire-token',
        type=str,
        help='Logfire token for observability (overrides environment variable)'
    )
    
    return parser.parse_args()

async def process_brand(
    brand: str,
    products: List[BlackpearlProduct],
    folders: List[DriveFolder],
    agent: MatchingAgent,
    results_db_conn,
    args,
    processed_product_ids: Set[int],
    product_task: TaskID,
    progress: Progress
) -> Dict[str, int]:
    """Process a single brand.
    
    Args:
        brand: Brand name
        products: List of products for this brand
        folders: List of folders for this brand
        agent: Matching agent
        results_db_conn: Connection to results database
        args: Command line arguments
        processed_product_ids: Set of already processed product IDs
        product_task: Progress bar task ID
        progress: Progress bar instance
        
    Returns:
        Dictionary with processing statistics
    """
    start_time = time.time()
    processed_count = 0
    match_count = 0
    
    # Apply limit if specified
    if args.limit > 0 and len(products) > args.limit:
        console.print(f"[yellow]Limiting to {args.limit} products for brand {brand}[/yellow]")
        products = products[:args.limit]
    
    # Update progress bar total
    progress.update(product_task, total=len(products))
    
    # Process each product
    for product in products:
        # Skip already processed products
        if product.id in processed_product_ids:
            console.print(f"[cyan]Skipping already processed product {product.id}: {product.descricao}[/cyan]")
            progress.update(product_task, advance=1)
            processed_count += 1
            continue
        
        try:
            # Find best match for this product
            match_result = await agent.find_best_match(product, folders)
            processed_count += 1
            
            # Save match if confidence is above threshold
            if match_result.confidence_score >= args.confidence_threshold:
                if not args.dry_run:
                    save_match_result(results_db_conn, match_result.model_dump())
                match_count += 1
            
            # Track progress for resumability
            if not args.dry_run:
                save_progress(results_db_conn, brand, product.id, True)
            
            # Log progress periodically
            if processed_count % 10 == 0:
                elapsed = time.time() - start_time
                log_progress(
                    brand=brand,
                    products_processed=processed_count,
                    products_total=len(products),
                    matches_found=match_count,
                    elapsed_seconds=elapsed
                )
            
            # Update progress bar
            progress.update(product_task, advance=1)
            
            # Add a small delay to avoid hitting API rate limits
            time.sleep(1)
            
        except Exception as e:
            # Print a more detailed representation of the exception
            console.print(f"[red]Error processing product {product.id}: {repr(e)}[/red]")
            # Log the error using str(e) for potentially cleaner logging service storage
            log_error(f"Error processing product {product.id}: {str(e)}", "process_brand_error", {
                "brand": brand,
                "product_id": product.id
            })
            
            # Still save progress to avoid reprocessing on resume
            if not args.dry_run:
                save_progress(results_db_conn, brand, product.id, False)
            
            # Update progress bar
            progress.update(product_task, advance=1)
    
    # Log final progress for this brand
    elapsed = time.time() - start_time
    log_progress(
        brand=brand,
        products_processed=processed_count,
        products_total=len(products),
        matches_found=match_count,
        elapsed_seconds=elapsed
    )
    
    return {
        "processed_count": processed_count,
        "match_count": match_count,
        "elapsed_seconds": elapsed
    }

async def main():
    """Main execution function."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Load environment variables
        load_dotenv()
        
        # Set up logging with optional token override
        setup_logging(args.logfire_token)
        
        console.print("[bold]Starting Product Folder Matcher[/bold]")
        
        # --- Database Connections ---
        # Path for the results database (matches, progress, etc.)
        results_db_path = args.output_db 
        # Path for the Drive catalog database (contains drive_items, drive_hierarchy)
        drive_catalog_db_path = "scripts/solid_stan/drive_catalog.db"  
        
        console.print(f"Connecting to Drive Catalog database: [cyan]{drive_catalog_db_path}[/cyan]")
        drive_catalog_conn = connect_sqlite_db(drive_catalog_db_path) # Connection for reading Drive data
        if not drive_catalog_conn:
            console.print("[red]Failed to connect to Drive Catalog DB. Exiting.[/red]")
            return

        console.print(f"Connecting to Results database: [cyan]{results_db_path}[/cyan]")
        results_conn = connect_sqlite_db(results_db_path) # Connection for writing results/progress
        if not results_conn:
            console.print("[red]Failed to connect to Results DB. Exiting.[/red]")
            if drive_catalog_conn: drive_catalog_conn.close()
            return
            
        pg_conn = connect_postgres_db()
        if not pg_conn:
            console.print("[red]Failed to connect to Postgres DB. Exiting.[/red]")
            if drive_catalog_conn: drive_catalog_conn.close()
            if results_conn: results_conn.close()
            return

        # Ensure results/progress tables exist in the results database
        create_results_tables(results_conn)
        create_progress_table(results_conn)
        # --- End Database Connections ---

        # Initialize tools with the Drive Catalog connection for reading folder data
        tools = ProductFolderMatcherTools(drive_catalog_conn) 
        agent = MatchingAgent(tools, model_name=args.model)
        
        # Handle resumability - read progress from the results database
        processed_product_ids = set()
        last_brand = None
        last_product_id = None
        
        if not args.restart:
            processed_product_ids = get_processed_products(results_conn) # Use results_conn
            last_brand, last_product_id = get_last_brand_product(results_conn) # Use results_conn
            
            if last_brand and last_product_id:
                console.print(f"[green]Resuming from previous execution. Last processed product: {last_product_id} in brand {last_brand}[/green]")
                console.print(f"[green]Already processed {len(processed_product_ids)} products[/green]")
        else:
            console.print("[yellow]Restarting matching process from beginning[/yellow]")
        
        # Fetch products from Postgres
        console.print("[cyan]Fetching products from Blackpearl database...[/cyan]")
        products_by_brand = get_products_by_brand(pg_conn, args.brand)
        
        # Fetch folders from the Drive catalog database
        console.print("[cyan]Fetching folders from Drive catalog...[/cyan]")
        folders_by_brand = get_folders_by_brand(drive_catalog_conn, args.brand) # Use drive_catalog_conn
        
        # Get common brands (exist in both systems)
        common_brands = set(products_by_brand.keys()) & set(folders_by_brand.keys())
        console.print(f"[green]Found {len(common_brands)} brands present in both systems[/green]")
        
        # Filter empty brands
        valid_brands = []
        for brand in common_brands:
            products = products_by_brand[brand]
            folders = folders_by_brand[brand]
            
            if products and folders:
                valid_brands.append((brand, len(products), len(folders)))
        
        # Sort by brand name
        valid_brands.sort(key=lambda x: x[0])
        
        if not valid_brands:
            console.print("[red]No valid brands found with both products and folders[/red]")
            return
        
        # Display brands before processing
        brand_table = Table(title="Brands to Process")
        brand_table.add_column("Brand", style="cyan")
        brand_table.add_column("Products", style="green")
        brand_table.add_column("Folders", style="yellow")
        
        for brand, product_count, folder_count in valid_brands:
            brand_table.add_row(brand, str(product_count), str(folder_count))
        
        console.print(brand_table)
        
        # Confirm before proceeding
        if not args.dry_run and not args.brand:
            if not input("Press Enter to continue or Ctrl+C to abort..."):
                pass
        
        # Process each brand
        resume_flag = False if args.restart else True
        
        # Track overall statistics
        total_processed = 0
        total_matched = 0
        brand_stats = {}
        
        with Progress() as progress:
            brand_task = progress.add_task("[cyan]Processing brands...", total=len(valid_brands))
            product_task = progress.add_task("[green]Processing products...", total=0)
            
            for brand, product_count, folder_count in valid_brands:
                brand_name, products, folders = brand, products_by_brand[brand], folders_by_brand[brand]
                
                # Skip brands until we reach the last processed brand (for resuming)
                if resume_flag and last_brand and brand_name != last_brand:
                    console.print(f"[yellow]Skipping brand {brand_name} (resuming from {last_brand})[/yellow]")
                    progress.update(brand_task, advance=1)
                    continue
                
                # Once we hit the last brand, we've reached our resume point
                if resume_flag and last_brand and brand_name == last_brand:
                    resume_flag = False
                    console.print(f"[green]Resuming processing at brand {brand_name}[/green]")
                
                console.print(f"[bold cyan]Processing brand: {brand_name} ({product_count} products, {folder_count} folders)[/bold cyan]")
                
                # Process the brand
                stats = await process_brand(
                    brand=brand_name,
                    products=products,
                    folders=folders,
                    agent=agent,
                    results_db_conn=results_conn,
                    args=args,
                    processed_product_ids=processed_product_ids,
                    product_task=product_task,
                    progress=progress
                )
                
                # Update statistics
                total_processed += stats["processed_count"]
                total_matched += stats["match_count"]
                brand_stats[brand_name] = stats
                
                # Reset product progress for next brand
                progress.update(product_task, total=0, completed=0)
                
                # Update brand progress
                progress.update(brand_task, advance=1)
                
                # Add newly processed products to the set
                processed_product_ids.update([p.id for p in products])
        
        # Check for duplicate matches
        if not args.dry_run:
            console.print("[cyan]Checking for duplicate matches...[/cyan]")
            duplicates = check_and_record_duplicates(results_conn)
            
            if duplicates:
                duplicate_table = Table(title="Duplicate Matches (Products sharing the same folder)")
                duplicate_table.add_column("Folder", style="cyan")
                duplicate_table.add_column("Product Count", style="red")
                duplicate_table.add_column("Product IDs", style="yellow")
                
                for dup in duplicates[:10]:  # Show at most 10
                    duplicate_table.add_row(
                        dup["drive_folder_id"],
                        str(dup["product_count"]),
                        dup["product_ids"]
                    )
                
                if len(duplicates) > 10:
                    console.print(f"[yellow]Showing 10 of {len(duplicates)} duplicates...[/yellow]")
                
                console.print(duplicate_table)
        
        # Generate summary report
        console.print("[cyan]Generating summary report...[/cyan]")
        summary = generate_summary_report(results_conn)
        
        # Display summary
        summary_panel = Panel(
            f"""[bold]Matching Process Summary[/bold]
            
Total Products Processed: {total_processed}
Total Matches Found: {total_matched}
High Confidence Matches (>= 0.9): {summary.get('high_confidence', 0)}
Medium Confidence Matches (0.8-0.9): {summary.get('medium_confidence', 0)}
Low Confidence Matches (< 0.8): {summary.get('low_confidence', 0)}
Duplicate Matches: {summary.get('duplicate_count', 0)}
            
Results saved to: {args.output_db}
            """,
            title="Summary",
            border_style="green"
        )
        
        console.print(summary_panel)
        
        # Brand statistics
        brand_stats_table = Table(title="Brand Processing Statistics")
        brand_stats_table.add_column("Brand", style="cyan")
        brand_stats_table.add_column("Processed", style="green")
        brand_stats_table.add_column("Matched", style="yellow")
        brand_stats_table.add_column("Success Rate", style="magenta")
        brand_stats_table.add_column("Time (s)", style="blue")
        
        for brand, stats in brand_stats.items():
            success_rate = f"{stats['match_count'] / max(1, stats['processed_count']) * 100:.1f}%"
            brand_stats_table.add_row(
                brand,
                str(stats["processed_count"]),
                str(stats["match_count"]),
                success_rate,
                f"{stats['elapsed_seconds']:.1f}"
            )
        
        console.print(brand_stats_table)
        
        # Clean up connections
        if drive_catalog_conn:
            drive_catalog_conn.close()
            console.print("[green]Closed Drive Catalog database connection.[/green]")
        if results_conn:
            results_conn.close()
            console.print("[green]Closed Results database connection.[/green]")
        if pg_conn:
            pg_conn.close()
            console.print("[green]Closed Blackpearl database connection.[/green]")
        
        console.print("[bold green]Matching process complete![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {str(e)}[/red]")
        log_error(f"Unexpected error in main: {str(e)}", "main_error", {})
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
    # Ensure a clean exit
    sys.exit(0) 