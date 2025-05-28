#!/bin/bash

# Demo: How health check integrates with Makefile
# Part of NMSTX-105: Health check system implementation

# Simulate Makefile targets

case "${1:-health}" in
    "health")
        echo "🎯 Running: make health"
        echo ""
        ./scripts/health_check.sh
        ;;
    "health-quick")
        echo "🎯 Running: make health-quick"
        echo ""
        ./scripts/health_check.sh --quick
        ;;
    "health-detailed")
        echo "🎯 Running: make health-detailed"
        echo ""
        ./scripts/health_check.sh --detailed
        ;;
    "health-api")
        echo "🎯 Running: make health-api"
        echo ""
        ./scripts/health_check.sh --service api
        ;;
    "health-db")
        echo "🎯 Running: make health-db"
        echo ""
        ./scripts/health_check.sh --service postgres
        ;;
    "help")
        echo "Available health commands:"
        echo "  make health          - Full health check"
        echo "  make health-quick    - Quick critical services check"
        echo "  make health-detailed - Detailed health with system info"
        echo "  make health-api      - Check API service only"
        echo "  make health-db       - Check database only"
        echo ""
        echo "Individual service checks:"
        echo "  ./scripts/health_check.sh --service <service>"
        echo "  Available services: api, postgres, neo4j, graphiti"
        echo ""
        echo "Examples:"
        echo "  ./scripts/makefile_health_demo.sh health"
        echo "  ./scripts/makefile_health_demo.sh health-quick"
        echo "  TIMEOUT=10 ./scripts/makefile_health_demo.sh health"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './scripts/makefile_health_demo.sh help' for available commands"
        exit 1
        ;;
esac 