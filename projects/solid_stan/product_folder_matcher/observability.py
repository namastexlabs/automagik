"""Logfire setup and logging utilities for product folder matcher."""

import os
import logfire
from rich.console import Console
from typing import Dict, Any, Optional

# Initialize console for rich output
console = Console()

def setup_logging(token: Optional[str] = None):
    """Set up Logfire for observability.
    
    Args:
        token: Logfire token. If None, will attempt to use environment variable.
    """
    try:
        # Try to import settings from src
        from automagik.config import settings
        token = token or settings.LOGFIRE_TOKEN
    except ImportError:
        # Fallback to environment variable
        token = token or os.getenv("LOGFIRE_TOKEN")
    
    if token:
        os.environ["LOGFIRE_TOKEN"] = token
        logfire.configure(scrubbing=False, console=False)
        
        # Instrument libraries for better tracing
        logfire.instrument_pydantic_ai()
        
      
        console.print("[green]Logfire initialized successfully[/green]")
        logfire.info("Logfire initialized", component="product_folder_matcher")
        return True
    else:
        console.print("[yellow]Warning: No Logfire token provided. Logging disabled.[/yellow]")
        return False

def log_database_connection(db_type: str, host: str, database: str, success: bool):
    """Log database connection attempt."""
    if success:
        logfire.info(
            f"{db_type} database connected",
            db_type=db_type,
            host=host,
            database=database
        )
    else:
        logfire.error(
            f"{db_type} database connection failed",
            db_type=db_type,
            host=host,
            database=database
        )

def log_agent_request(prompt: str, product_id: int, brand: str):
    """Log an agent request."""
    logfire.info(
        "Agent request",
        product_id=product_id,
        brand=brand,
        prompt_length=len(prompt)
    )

def log_agent_response(response: Dict[str, Any], product_id: int, brand: str, latency_ms: float):
    """Log an agent response."""
    logfire.info(
        "Agent response received",
        product_id=product_id,
        brand=brand,
        confidence=response.get("confidence_score", 0),
        latency_ms=latency_ms
    )

def log_match_result(match_result: Dict[str, Any], threshold: float):
    """Log a match result."""
    confidence = match_result.get("confidence_score", 0)
    
    if confidence >= threshold:
        logfire.info(
            "Product matched successfully",
            product_id=match_result.get("product_id"),
            drive_folder_id=match_result.get("drive_folder_id"),
            confidence=confidence,
            passed_threshold=True
        )
    else:
        logfire.warning(
            "Product match below threshold",
            product_id=match_result.get("product_id"),
            drive_folder_id=match_result.get("drive_folder_id", "none"),
            confidence=confidence,
            threshold=threshold,
            passed_threshold=False
        )

def log_progress(brand: str, products_processed: int, products_total: int, 
                 matches_found: int, elapsed_seconds: float):
    """Log processing progress."""
    logfire.info(
        "Processing progress",
        brand=brand,
        products_processed=products_processed,
        products_total=products_total,
        matches_found=matches_found,
        completion_percent=round(products_processed / max(1, products_total) * 100, 2),
        elapsed_seconds=elapsed_seconds,
        estimated_remaining_seconds=elapsed_seconds * (products_total - products_processed) / max(1, products_processed)
    )

def log_error(error_message: str, error_type: str, context: Dict[str, Any]):
    """Log an error with context."""
    logfire.error(
        error_message,
        error_type=error_type,
        **context
    ) 