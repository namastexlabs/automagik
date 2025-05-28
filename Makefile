# ===========================================
# 💜 Automagik Agents - Makefile
# ===========================================
# Production-grade AI agent deployment automation
# Designed for AI agents to parse and execute

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ===========================================
# 💜 COLORS & STYLING
# ===========================================
PURPLE := \033[0;35m
BOLD_PURPLE := \033[1;35m
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m
CHECKMARK := ✅
WARNING := ⚠️
ERROR := ❌
ROCKET := 🚀
GEAR := ⚙️

# ===========================================
# 💜 CONFIGURATION
# ===========================================
PROJECT_ROOT := $(shell pwd)
VENV_PATH := $(PROJECT_ROOT)/.venv
PYTHON := $(VENV_PATH)/bin/python
PIP := $(VENV_PATH)/bin/pip
UV := $(VENV_PATH)/bin/uv

# Force flag support
FORCE ?=
ifdef FORCE
	FORCE_FLAG := --force
else
	FORCE_FLAG :=
endif

# Environment detection
ENV_FILE := .env
PROD_ENV_FILE := .env.prod
ifeq ($(wildcard $(PROD_ENV_FILE)),)
	ACTIVE_ENV := development
	ACTIVE_ENV_FILE := $(ENV_FILE)
else
	ACTIVE_ENV := production
	ACTIVE_ENV_FILE := $(PROD_ENV_FILE)
endif

# Docker configuration
DOCKER_COMPOSE_FILE := docker/docker-compose.yml
DOCKER_COMPOSE_PROD_FILE := docker/docker-compose-prod.yml
CONTAINER_PREFIX := automagik

# ===========================================
# 💜 UTILITY FUNCTIONS
# ===========================================
define print_banner
	@echo ""
	@echo "$(BOLD_PURPLE)╔═══════════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BOLD_PURPLE)║                        💜 AUTOMAGIK AGENTS                           ║$(NC)"
	@echo "$(BOLD_PURPLE)║                     AI Agent Framework Manager                       ║$(NC)"
	@echo "$(BOLD_PURPLE)╚═══════════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
endef

define print_section
	@echo ""
	@echo "$(PURPLE)$(1)$(NC)"
	@echo "$(PURPLE)$(shell printf '=%.0s' {1..$(shell echo '$(1)' | wc -c)})$(NC)"
endef

define print_status
	@echo "$(PURPLE)💜 $(1)$(NC)"
endef

define print_success
	@echo "$(GREEN)$(CHECKMARK) $(1)$(NC)"
endef

define print_warning
	@echo "$(YELLOW)$(WARNING) $(1)$(NC)"
endef

define print_error
	@echo "$(RED)$(ERROR) $(1)$(NC)"
endef

define check_env_file
	@if [ ! -f "$(1)" ]; then \
		$(call print_error,Environment file $(1) not found); \
		echo "$(YELLOW)💡 Copy .env.example to $(1) and configure it$(NC)"; \
		exit 1; \
	fi
endef

define check_venv
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found at $(VENV_PATH)); \
		echo "$(YELLOW)💡 Run 'make install-dev' to set up the environment$(NC)"; \
		exit 1; \
	fi
endef

define check_docker
	@if ! command -v docker >/dev/null 2>&1; then \
		$(call print_error,Docker not found); \
		echo "$(YELLOW)💡 Install Docker first: https://docs.docker.com/get-docker/$(NC)"; \
		exit 1; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		$(call print_error,Docker Compose not found); \
		echo "$(YELLOW)💡 Install Docker Compose: https://docs.docker.com/compose/install/$(NC)"; \
		exit 1; \
	fi
endef

define detect_mode
	if [ -f "$(DOCKER_COMPOSE_FILE)" ] && docker-compose -f $(DOCKER_COMPOSE_FILE) ps | grep -q Up; then \
		echo "docker"; \
	elif [ -f "$(DOCKER_COMPOSE_PROD_FILE)" ] && docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) ps | grep -q Up; then \
		echo "docker-prod"; \
	elif pgrep -f "uvicorn.*automagik" >/dev/null 2>&1; then \
		echo "local"; \
	else \
		echo "none"; \
	fi
endef

# ===========================================
# 💜 PHONY TARGETS
# ===========================================
.PHONY: help install start stop restart status logs health dev docker prod
.PHONY: install-dev install-docker install-prod clean reset test lint format
.PHONY: db-init db-migrate db-reset docker-build docker-clean
.PHONY: requirements-update venv-create venv-clean check-system

# ===========================================
# 💜 HELP SYSTEM
# ===========================================
help: ## 💜 Show this help message
	$(call print_banner)
	@echo "$(CYAN)Environment: $(ACTIVE_ENV) (using $(ACTIVE_ENV_FILE))$(NC)"
	@echo ""
	$(call print_section,🚀 Quick Start)
	@echo "  $(PURPLE)make install-dev$(NC)    Install development environment"
	@echo "  $(PURPLE)make dev$(NC)            Start in development mode"
	@echo "  $(PURPLE)make docker$(NC)         Start Docker development stack"
	@echo "  $(PURPLE)make prod$(NC)           Start production Docker stack"
	@echo ""
	$(call print_section,📋 Installation)
	@echo "  $(PURPLE)install-dev$(NC)         Install development environment with venv"
	@echo "  $(PURPLE)install-docker$(NC)      Set up Docker development environment"
	@echo "  $(PURPLE)install-prod$(NC)        Set up production Docker environment"
	@echo ""
	$(call print_section,🎛️ Service Management)
	@echo "  $(PURPLE)start$(NC)               Start services (auto-detect mode)"
	@echo "  $(PURPLE)stop$(NC)                Stop all services"
	@echo "  $(PURPLE)restart$(NC)             Restart services"
	@echo "  $(PURPLE)status$(NC)              Show PM2-style status table"
	@echo "  $(PURPLE)logs$(NC)                View colorized logs"
	@echo "  $(PURPLE)health$(NC)              Check health of all services"
	@echo ""
	$(call print_section,🛠️ Development)
	@echo "  $(PURPLE)test$(NC)                Run test suite"
	@echo "  $(PURPLE)lint$(NC)                Run code linting"
	@echo "  $(PURPLE)format$(NC)              Format code with ruff"
	@echo "  $(PURPLE)requirements-update$(NC) Update Python dependencies"
	@echo ""
	$(call print_section,🗄️ Database)
	@echo "  $(PURPLE)db-init$(NC)             Initialize database"
	@echo "  $(PURPLE)db-migrate$(NC)          Run database migrations"
	@echo "  $(PURPLE)db-reset$(NC)            Reset database (WARNING: destructive)"
	@echo ""
	$(call print_section,🐳 Docker)
	@echo "  $(PURPLE)docker-build$(NC)        Build Docker images"
	@echo "  $(PURPLE)docker-clean$(NC)        Clean Docker images and containers"
	@echo ""
	$(call print_section,🧹 Maintenance)
	@echo "  $(PURPLE)clean$(NC)               Clean temporary files"
	@echo "  $(PURPLE)reset$(NC)               Full reset (WARNING: destructive)"
	@echo "  $(PURPLE)check-system$(NC)        Check system prerequisites"
	@echo ""
	@echo "$(CYAN)💡 Use 'make <target> FORCE=1' to force operations that might conflict$(NC)"
	@echo ""

# ===========================================
# 💜 SYSTEM CHECKS
# ===========================================
check-system: ## 🔍 Check system prerequisites
	$(call print_status,Checking system prerequisites...)
	@echo ""
	@echo "$(PURPLE)Python:$(NC)"
	@python3 --version 2>/dev/null || (echo "$(RED)$(ERROR) Python 3 not found$(NC)" && exit 1)
	@echo "$(GREEN)$(CHECKMARK) Python 3 found$(NC)"
	@echo ""
	@echo "$(PURPLE)Docker:$(NC)"
	@docker --version 2>/dev/null || echo "$(YELLOW)$(WARNING) Docker not found - required for Docker mode$(NC)"
	@docker-compose --version 2>/dev/null || echo "$(YELLOW)$(WARNING) Docker Compose not found - required for Docker mode$(NC)"
	@echo ""
	@echo "$(PURPLE)Environment:$(NC)"
	@if [ -f "$(ACTIVE_ENV_FILE)" ]; then \
		echo "$(GREEN)$(CHECKMARK) Environment file $(ACTIVE_ENV_FILE) found$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) Environment file $(ACTIVE_ENV_FILE) not found$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)Virtual Environment:$(NC)"
	@if [ -d "$(VENV_PATH)" ]; then \
		echo "$(GREEN)$(CHECKMARK) Virtual environment found at $(VENV_PATH)$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) Virtual environment not found - run 'make install-dev'$(NC)"; \
	fi

# ===========================================
# 💜 STATUS DETECTION
# ===========================================
detect-mode: ## 🔍 Detect current running mode
	@echo "$(shell $(call detect_mode))"

# Internal target for checking if we should proceed with potentially destructive operations
check-force:
	@if [ -z "$(FORCE)" ]; then \
		$(call print_warning,This operation may conflict with running services); \
		echo "$(YELLOW)💡 Use 'make $@ FORCE=1' to proceed anyway$(NC)"; \
		exit 1; \
	fi

# ===========================================
# 💜 PM2-STYLE STATUS DISPLAY
# ===========================================
status: ## 📊 Show PM2-style status table
	$(call print_status,Automagik Agents Status)
	@echo ""
	@echo "$(BOLD_PURPLE)┌─────────────────┬──────────┬───────┬────────┬─────────┬──────────┐$(NC)"
	@echo "$(BOLD_PURPLE)│ Instance        │ Mode     │ Port  │ PID    │ Uptime  │ Status   │$(NC)"
	@echo "$(BOLD_PURPLE)├─────────────────┼──────────┼───────┼────────┼─────────┼──────────┤$(NC)"
	@$(call show_docker_status)
	@$(call show_local_status)
	@$(call show_service_status)
	@echo "$(BOLD_PURPLE)└─────────────────┴──────────┴───────┴────────┴─────────┴──────────┘$(NC)"
	@echo ""

status-quick: ## ⚡ Quick status summary
	@mode=$$($(call detect_mode)); \
	docker_count=$$(docker ps --filter "name=automagik" --format "{{.Names}}" 2>/dev/null | wc -l); \
	local_count=$$(pgrep -f "uvicorn.*automagik" | wc -l); \
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		service_active="active"; \
	else \
		service_active="inactive"; \
	fi; \
	echo "$(PURPLE)💜 Mode: $$mode | Docker: $$docker_count | Local: $$local_count | Service: $$service_active$(NC)"

define show_docker_status
	if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | grep -q "automagik"; then \
		docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "automagik" | while IFS=$$'\t' read -r name status ports; do \
			uptime=$$(echo "$$status" | sed 's/Up //g' | sed 's/ (.*//g'); \
			port=$$(echo "$$ports" | grep -o '[0-9]*->[0-9]*' | head -1 | cut -d'>' -f2 | cut -d'/' -f1); \
			if [ -z "$$port" ]; then \
				port=$$(echo "$$ports" | grep -o '[0-9]*:[0-9]*->[0-9]*' | head -1 | cut -d'>' -f2 | cut -d'/' -f1); \
			fi; \
			if [ -z "$$port" ]; then port="-"; fi; \
			container_id=$$(docker ps --format "{{.ID}}" --filter "name=$$name" | head -c 6); \
			if echo "$$status" | grep -q "Up"; then \
				status_icon="$(GREEN)● online$(NC)"; \
			else \
				status_icon="$(RED)● error$(NC)"; \
			fi; \
			printf "$(BOLD_PURPLE)│$(NC) %-15s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-7s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC)\n" \
				"$$(echo $$name | cut -c1-15)" "docker" "$$port" "$$container_id" "$$uptime" "$$status_icon"; \
		done; \
	fi
endef

define show_local_status
	if pgrep -f "uvicorn.*automagik" >/dev/null 2>&1; then \
		pid=$$(pgrep -f "uvicorn.*automagik"); \
		port=$$(netstat -tlnp 2>/dev/null | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		uptime=$$(ps -o etime= -p $$pid | tr -d ' '); \
		printf "$(BOLD_PURPLE)│$(NC) %-15s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-7s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC)\n" \
			"automagik-local" "process" "$$port" "$$pid" "$$uptime" "$(GREEN)● online$(NC)"; \
	else \
		printf "$(BOLD_PURPLE)│$(NC) %-15s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-7s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC)\n" \
			"automagik-local" "process" "-" "-" "-" "$(YELLOW)○ stopped$(NC)"; \
	fi
endef

define show_service_status
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		pid=$$(systemctl show automagik-agents --property=MainPID --value 2>/dev/null); \
		if [ "$$pid" != "0" ] && [ -n "$$pid" ]; then \
			port=$$(netstat -tlnp 2>/dev/null | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
			uptime=$$(systemctl show automagik-agents --property=ActiveEnterTimestamp --value 2>/dev/null | xargs -I {} date -d "{}" +%s 2>/dev/null | xargs -I {} echo "scale=0; ($$(date +%s) - {}) / 60" | bc 2>/dev/null || echo "0"); \
			if [ "$$uptime" -gt 60 ]; then \
				uptime="$$(echo "scale=0; $$uptime / 60" | bc)h $$(echo "$$uptime % 60" | bc)m"; \
			else \
				uptime="$${uptime}m"; \
			fi; \
			printf "$(BOLD_PURPLE)│$(NC) %-15s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-7s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC)\n" \
				"automagik-svc" "service" "$$port" "$$pid" "$$uptime" "$(GREEN)● online$(NC)"; \
		else \
			printf "$(BOLD_PURPLE)│$(NC) %-15s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-7s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC)\n" \
				"automagik-svc" "service" "-" "-" "-" "$(RED)● error$(NC)"; \
		fi; \
	else \
		printf "$(BOLD_PURPLE)│$(NC) %-15s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-7s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC)\n" \
			"automagik-svc" "service" "-" "-" "-" "$(YELLOW)○ stopped$(NC)"; \
	fi
endef 