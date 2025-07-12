#!/usr/bin/env python3
"""Test script for stream-json input functionality.

This script demonstrates how to send real-time messages to a Claude Code workflow
using the stream-json input format.

Usage:
    python test_stream_input.py | claudecode --input-format stream-json --output-format stream-json
"""

import json
import time
import sys


def send_message(message_type: str, message: str):
    """Send a stream-json formatted message to stdout."""
    message_data = {
        "type": message_type,
        "message": message
    }
    print(json.dumps(message_data))
    sys.stdout.flush()


def main():
    """Run the stream input test."""
    print("# Starting stream-json input test", file=sys.stderr)
    
    # Start with initial workflow message
    send_message("user", "Create a simple counter app with increment and decrement buttons")
    print("# Sent initial message", file=sys.stderr)
    
    # Wait for initial implementation to start
    time.sleep(5)
    
    # Add new requirement
    send_message("user", "Add a reset button that sets the counter to zero")
    print("# Sent reset button requirement", file=sys.stderr)
    
    # Wait a bit more
    time.sleep(3)
    
    # Add another requirement
    send_message("user", "Make the counter persistent using localStorage")
    print("# Sent persistence requirement", file=sys.stderr)
    
    # Add a system message for guidance
    time.sleep(2)
    send_message("system", "Focus on making the UI clean and responsive")
    print("# Sent system guidance", file=sys.stderr)
    
    # Final enhancement
    time.sleep(4)
    send_message("user", "Add keyboard shortcuts: Space to increment, Backspace to decrement")
    print("# Sent keyboard shortcuts requirement", file=sys.stderr)
    
    print("# Stream input test completed", file=sys.stderr)


if __name__ == "__main__":
    main()