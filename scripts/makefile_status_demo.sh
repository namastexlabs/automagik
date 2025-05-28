#!/bin/bash

# Demo: How status display integrates with Makefile
# Part of NMSTX-101: Status display implementation

# Simulate Makefile targets

case "${1:-status}" in
    "status")
        echo "🎯 Running: make status"
        echo ""
        ./scripts/status_display.sh
        ;;
    "status-verbose")
        echo "🎯 Running: make status-verbose"
        echo ""
        ./scripts/status_display.sh --verbose
        ;;
    "help")
        echo "Available status commands:"
        echo "  make status         - Show PM2-style status table"
        echo "  make status-verbose - Show detailed status with diagnostics"
        echo ""
        echo "Examples:"
        echo "  ./scripts/makefile_status_demo.sh status"
        echo "  ./scripts/makefile_status_demo.sh status-verbose"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './scripts/makefile_status_demo.sh help' for available commands"
        exit 1
        ;;
esac 