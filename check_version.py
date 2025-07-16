#!/usr/bin/env python3
"""Check version detection in different scenarios."""

import os
import sys

# First, show environment
print(f"Python: {sys.executable}")
print(f"AUTOMAGIK_VERSION env: {os.environ.get('AUTOMAGIK_VERSION', 'Not set')}")
print(f"Working directory: {os.getcwd()}")
print()

# Now try importing and checking version
try:
    from automagik.utils.version import __version__, _get_version
    print(f"Imported version: {__version__}")
    print(f"_get_version() result: {_get_version()}")
    
    # Show the version.py file location
    import automagik.utils.version
    print(f"version.py location: {automagik.utils.version.__file__}")
except Exception as e:
    print(f"Error importing: {e}")