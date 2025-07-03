"""
Main CLI entry point that simply re-exports the CLI app from the src.cli package.
"""
from automagik.cli import app

if __name__ == "__main__":
    app()
