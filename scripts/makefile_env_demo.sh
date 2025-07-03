#!/bin/bash

# Demo: How environment loader integrates with Makefile
# Part of NMSTX-108: Environment detection and loading implementation

# Source the environment loader functions
source ./scripts/env_loader.sh

# Simulate Makefile targets using the environment loader

case "${1:-env-info}" in
    "env-info")
        echo "🎯 Running: make env-info"
        echo ""
        ./scripts/env_loader.sh info
        ;;
    "env-validate")
        echo "🎯 Running: make env-validate" 
        echo ""
        ./scripts/env_loader.sh validate
        ;;
    "env-load")
        echo "🎯 Running: make env-load"
        echo ""
        ./scripts/env_loader.sh load
        ;;
    "env-detect")
        echo "🎯 Running: make env-detect"
        echo ""
        mode=$(./scripts/env_loader.sh detect)
        echo "Detected mode: $mode"
        ;;
    "env-get-port")
        echo "🎯 Running: make env-get-port"
        echo ""
        port=$(./scripts/env_loader.sh get-port)
        echo "AUTOMAGIK_API_PORT: $port"
        
        # Show other ports too
        postgres_port=$(./scripts/env_loader.sh get-port POSTGRES_PORT 5432)
        echo "POSTGRES_PORT: $postgres_port"
        ;;
    "env-check-features")
        echo "🎯 Running: make env-check-features"
        echo ""
        echo "Feature support:"
        
        features=("neo4j" "graphiti" "discord" "notion")
        for feature in "${features[@]}"; do
            supported=$(./scripts/env_loader.sh supports "$feature")
            if [[ "$supported" == "yes" ]]; then
                echo "  ✅ $feature: enabled"
            else
                echo "  ❌ $feature: disabled"
            fi
        done
        ;;
    "start-dev")
        echo "🎯 Running: make start-dev (with environment loading)"
        echo ""
        
        # Load environment
        echo "🔄 Loading environment..."
        if ./scripts/env_loader.sh load >/dev/null 2>&1; then
            echo "✅ Environment loaded"
        else
            echo "❌ Failed to load environment"
            exit 1
        fi
        
        # Validate environment
        echo "🔍 Validating environment..."
        if ./scripts/env_loader.sh validate >/dev/null 2>&1; then
            echo "✅ Environment validated"
        else
            echo "❌ Environment validation failed"
            ./scripts/env_loader.sh validate
            exit 1
        fi
        
        # Get port
        port=$(./scripts/env_loader.sh get-port)
        echo "🚀 Starting development server on port $port..."
        echo "   (would run: uvicorn src.main:app --host 0.0.0.0 --port $port --reload)"
        ;;
    "start-prod")
        echo "🎯 Running: make start-prod (with production environment)"
        echo ""
        
        # Force production mode detection
        mode=$(./scripts/env_loader.sh detect)
        if [[ "$mode" != "production" ]]; then
            echo "⚠️  Not in production mode, detected: $mode"
            echo "   (would normally switch to .env.prod)"
        fi
        
        # Load and validate
        ./scripts/env_loader.sh load
        ./scripts/env_loader.sh validate
        
        port=$(./scripts/env_loader.sh get-port)
        echo "🚀 Starting production server on port $port..."
        echo "   (would run: docker-compose -f docker/docker-compose-prod.yml up -d)"
        ;;
    "debug-env")
        echo "🎯 Running: make debug-env"
        echo ""
        echo "🔍 Environment Debug Information:"
        echo ""
        
        # Show all environment details
        ./scripts/env_loader.sh info
        echo ""
        
        # Show specific variables
        echo "🔧 Key Variables:"
        vars=("AUTOMAGIK_API_PORT" "ENVIRONMENT" "DATABASE_URL" "POSTGRES_HOST" "POSTGRES_PORT")
        for var in "${vars[@]}"; do
            value=$(./scripts/env_loader.sh get-var "$var")
            if [[ -n "$value" ]]; then
                echo "  $var: $value"
            else
                echo "  $var: (not set)"
            fi
        done
        ;;
    "help")
        echo "Available environment commands:"
        echo "  make env-info           - Show environment information"
        echo "  make env-validate       - Validate environment variables"
        echo "  make env-load           - Load environment variables"
        echo "  make env-detect         - Detect environment mode"
        echo "  make env-get-port       - Get port configuration"
        echo "  make env-check-features - Check feature support"
        echo "  make start-dev          - Start with environment loading"
        echo "  make start-prod         - Start production with env detection"
        echo "  make debug-env          - Debug environment configuration"
        echo ""
        echo "Direct script usage:"
        echo "  ./scripts/env_loader.sh help"
        echo ""
        echo "Examples:"
        echo "  ./scripts/makefile_env_demo.sh env-info"
        echo "  ./scripts/makefile_env_demo.sh start-dev"
        echo "  ./scripts/makefile_env_demo.sh debug-env"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './scripts/makefile_env_demo.sh help' for available commands"
        exit 1
        ;;
esac 