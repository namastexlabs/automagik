# ===========================================
# 🪄 Automagik Agents - Streamlined Makefile
# ===========================================

.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash

# ===========================================
# 🎨 Colors & Symbols
# ===========================================
PURPLE := \033[0;35m
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m
CHECKMARK := ✅
WARNING := ⚠️
ERROR := ❌
MAGIC := 🪄

# ===========================================
# 📁 Paths & Configuration
# ===========================================
PROJECT_ROOT := $(shell pwd)
VENV_PATH := $(PROJECT_ROOT)/.venv
PYTHON := $(VENV_PATH)/bin/python
DOCKER_COMPOSE_DEV := docker/docker-compose.yml
DOCKER_COMPOSE_PROD := docker/docker-compose-prod.yml

# Docker Compose command detection
DOCKER_COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

# Enable Docker Compose bake for better build performance
export COMPOSE_BAKE := true

# Log parameters
N ?= 100
FOLLOW ?=

# ===========================================
# 🛠️ Utility Functions
# ===========================================
define print_status
	@echo -e "$(PURPLE)🪄 $(1)$(NC)"
endef

define print_success
	@echo -e "$(GREEN)$(CHECKMARK) $(1)$(NC)"
endef

define print_warning
	@echo -e "$(YELLOW)$(WARNING) $(1)$(NC)"
endef

define print_error
	@echo -e "$(RED)$(ERROR) $(1)$(NC)"
endef

define check_docker
	@if ! command -v docker >/dev/null 2>&1; then \
		$(call print_error,Docker not found); \
		echo -e "$(YELLOW)💡 Install Docker: https://docs.docker.com/get-docker/$(NC)"; \
		exit 1; \
	fi
	@if ! docker info >/dev/null 2>&1; then \
		$(call print_error,Docker daemon not running); \
		echo -e "$(YELLOW)💡 Start Docker service$(NC)"; \
		exit 1; \
	fi
endef

define check_env_file
	@if [ ! -f ".env" ]; then \
		$(call print_warning,.env file not found); \
		echo -e "$(CYAN)Copying .env.example to .env...$(NC)"; \
		cp .env.example .env; \
		$(call print_success,.env created from example); \
		echo -e "$(YELLOW)💡 Edit .env and add your API keys$(NC)"; \
	fi
endef

define detect_graphiti_profile
	if [ -f ".env" ] && grep -q "NEO4J_URI" .env && grep -q "NEO4J_USERNAME" .env; then \
		echo "--profile graphiti"; \
	else \
		echo ""; \
	fi
endef

# ===========================================
# 📋 Help System
# ===========================================
.PHONY: help
help: ## 🪄 Show this help message
	@echo ""
	@echo -e "$(PURPLE)🪄 Automagik Agents - Streamlined Commands$(NC)"
	@echo ""
	@echo -e "$(CYAN)🚀 Installation:$(NC)"
	@echo -e "  $(PURPLE)install$(NC)         Install as systemd service"
	@echo -e "  $(PURPLE)install-dev$(NC)     Install development environment (uv sync)"
	@echo -e "  $(PURPLE)install-docker$(NC)  Install Docker development stack"
	@echo -e "  $(PURPLE)install-prod$(NC)    Install production Docker stack"
	@echo ""
	@echo -e "$(CYAN)🎛️ Service Management:$(NC)"
	@echo -e "  $(PURPLE)dev$(NC)             Start development mode (local Python)"
	@echo -e "  $(PURPLE)docker$(NC)          Start Docker development stack"
	@echo -e "  $(PURPLE)prod$(NC)            Start production Docker stack"
	@echo -e "  $(PURPLE)stop$(NC)            Stop development automagik-agents container only"
	@echo -e "  $(PURPLE)stop-prod$(NC)       Stop production automagik-agents container only"
	@echo -e "  $(PURPLE)stop-all$(NC)        Stop all services (DB, Neo4j, Graphiti, etc.)"
	@echo -e "  $(PURPLE)restart$(NC)         Restart services"
	@echo -e "  $(PURPLE)status$(NC)          Show service status"
	@echo ""
	@echo -e "$(CYAN)📋 Logs & Monitoring:$(NC)"
	@echo -e "  $(PURPLE)logs$(NC)            Show last 100 log lines"
	@echo -e "  $(PURPLE)logs N=50$(NC)       Show last N log lines"
	@echo -e "  $(PURPLE)logs FOLLOW=1$(NC)   Follow logs in real-time"
	@echo -e "  $(PURPLE)health$(NC)          Check service health"
	@echo ""
	@echo -e "$(CYAN)🔄 Maintenance:$(NC)"
	@echo -e "  $(PURPLE)update$(NC)          Update and restart services"
	@echo -e "  $(PURPLE)clean$(NC)           Clean temporary files"
	@echo -e "  $(PURPLE)test$(NC)            Run test suite"
	@echo ""
	@echo -e "$(YELLOW)💡 Neo4j/Graphiti auto-detected from .env$(NC)"
	@echo ""

# ===========================================
# 🚀 Installation Targets
# ===========================================
.PHONY: install install-dev install-docker install-prod
install: ## ⚙️ Install as systemd service
	$(call print_status,Installing systemd service...)
	@$(MAKE) install-dev
	@$(call check_env_file)
	@$(call create_systemd_service)
	@sudo systemctl daemon-reload
	@sudo systemctl enable automagik-agents
	$(call print_success,Systemd service installed!)
	@echo -e "$(CYAN)💡 Start with: sudo systemctl start automagik-agents$(NC)"

install-dev: ## 🛠️ Install development environment
	$(call print_status,Installing development environment...)
	@$(call check_prerequisites)
	@$(call setup_python_env)
	@$(call check_env_file)
	$(call print_success,Development environment ready!)

install-docker: ## 🐳 Install Docker development stack
	$(call print_status,Installing Docker development stack...)
	@$(call check_docker)
	@$(call check_env_file)
	@$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env build
	@$(call print_status,Starting Docker development stack...)
	@profile=$$($(call detect_graphiti_profile)); \
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env $$profile up -d
	$(call print_success,Docker development stack ready!)

install-prod: ## 🏭 Install production Docker stack
	$(call print_status,Installing production Docker stack...)
	@$(call check_docker)
	@if [ ! -f ".env.prod" ]; then \
		$(call print_error,.env.prod file not found); \
		echo -e "$(YELLOW)💡 Create .env.prod for production$(NC)"; \
		exit 1; \
	fi
	@$(call print_status,Building production containers...)
	@env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) build
	@$(call print_status,Starting production Docker stack...)
	@env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) up -d
	$(call print_success,Production Docker stack ready!)

# ===========================================
# 🎛️ Service Management
# ===========================================
.PHONY: dev docker prod stop stop-prod stop-all restart status
dev: ## 🛠️ Start development mode
	$(call print_status,Starting development mode...)
	@$(call check_env_file)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found); \
		echo -e "$(YELLOW)💡 Run 'make install-dev' first$(NC)"; \
		exit 1; \
	fi
	@$(call print_status,Activating virtual environment and starting...)
	@. $(VENV_PATH)/bin/activate && AM_FORCE_DEV_ENV=1 python -m src

docker: ## 🐳 Start Docker development stack
	@$(call print_status,Starting Docker development stack...)
	@$(call check_docker)
	@$(call check_env_file)
	@profile=$$($(call detect_graphiti_profile)); \
	$(call print_status,Starting services$$profile...); \
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env $$profile up -d
	@$(call print_success,Docker stack started!)

prod: ## 🏭 Start production Docker stack
	$(call print_status,Starting production Docker stack...)
	@$(call check_docker)
	@if [ ! -f ".env.prod" ]; then \
		$(call print_error,.env.prod not found); \
		exit 1; \
	fi
	@env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) up -d
	$(call print_success,Production stack started!)

stop: ## 🛑 Stop development automagik-agents container only
	$(call print_status,Stopping development automagik-agents container...)
	@sudo systemctl stop automagik-agents 2>/dev/null || true
	@docker stop automagik-agents-dev 2>/dev/null || true
	@pkill -f "python.*src" 2>/dev/null || true
	$(call print_success,Development automagik-agents stopped!)

stop-prod: ## 🛑 Stop production automagik-agents container only
	$(call print_status,Stopping production automagik-agents container...)
	@docker stop automagik-agents-prod 2>/dev/null || true
	$(call print_success,Production automagik-agents stopped!)

stop-all: ## 🛑 Stop all services (preserves containers)
	$(call print_status,Stopping all services...)
	@sudo systemctl stop automagik-agents 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env --profile graphiti stop 2>/dev/null || true
	@if [ -f ".env.prod" ]; then \
		env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) stop 2>/dev/null || true; \
	else \
		$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) --env-file .env stop 2>/dev/null || true; \
	fi
	@pkill -f "python.*src" 2>/dev/null || true
	$(call print_success,All services stopped!)

restart: ## 🔄 Restart services
	@$(MAKE) stop-all
	@sleep 2
	@if systemctl is-enabled automagik-agents >/dev/null 2>&1; then \
		sudo systemctl start automagik-agents; \
	elif docker ps -a --filter "name=automagik-agents-prod" --format "{{.Names}}" | grep -q prod; then \
		$(MAKE) prod; \
	elif docker ps -a --filter "name=automagik-agents-dev" --format "{{.Names}}" | grep -q dev; then \
		$(MAKE) docker; \
	else \
		$(call print_warning,No previous service detected); \
	fi

status: ## 📊 Show service status
	$(call print_status,Service Status)
	@echo ""
	@echo -e "$(PURPLE)┌─────────────────────────┬──────────┬─────────┬──────────┐$(NC)"
	@echo -e "$(PURPLE)│ Service                 │ Status   │ Port    │ PID      │$(NC)"
	@echo -e "$(PURPLE)├─────────────────────────┼──────────┼─────────┼──────────┤$(NC)"
	@$(call show_systemd_status)
	@$(call show_docker_status)
	@$(call show_local_status)
	@echo -e "$(PURPLE)└─────────────────────────┴──────────┴─────────┴──────────┘$(NC)"

# ===========================================
# 📋 Logs & Monitoring
# ===========================================
.PHONY: logs health
logs: ## 📄 View logs (use N=lines, FOLLOW=1 for tail -f)
	@if [ "$(FOLLOW)" = "1" ]; then \
		echo -e "$(PURPLE)🪄 Following logs - Press Ctrl+C to stop$(NC)"; \
		if systemctl is-active automagik-agents >/dev/null 2>&1; then \
			journalctl -u automagik-agents -f --no-pager | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1 | grep -q automagik; then \
			container=$$(docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1); \
			docker logs -f $$container 2>&1 | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif [ -f "logs/automagik.log" ]; then \
			tail -f logs/automagik.log | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		else \
			echo -e "$(YELLOW)⚠️ No log sources found to follow$(NC)"; \
		fi; \
	else \
		echo -e "$(PURPLE)🪄 Showing last $(N) log lines$(NC)"; \
		if systemctl is-active automagik-agents >/dev/null 2>&1; then \
			journalctl -u automagik-agents -n $(N) --no-pager | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1 | grep -q automagik; then \
			container=$$(docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1); \
			docker logs --tail $(N) $$container 2>&1 | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif [ -f "logs/automagik.log" ]; then \
			tail -n $(N) logs/automagik.log | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		else \
			echo -e "$(YELLOW)⚠️ No log sources found$(NC)"; \
		fi; \
	fi

health: ## 💊 Check service health
	$(call print_status,Health Check)
	@$(call check_health)

# ===========================================
# 🔄 Maintenance
# ===========================================
.PHONY: update clean test
update: ## 🔄 Update and restart services
	$(call print_status,Updating Automagik Agents...)
	@$(MAKE) stop-all
	@git pull
	@if systemctl is-enabled automagik-agents >/dev/null 2>&1; then \
		$(MAKE) install-dev && sudo systemctl start automagik-agents; \
	elif docker ps -a --filter "name=automagik-agents-prod" --format "{{.Names}}" | grep -q prod; then \
		$(MAKE) install-prod; \
	elif docker ps -a --filter "name=automagik-agents-dev" --format "{{.Names}}" | grep -q dev; then \
		$(MAKE) install-docker; \
	else \
		$(call print_warning,No previous installation detected); \
	fi
	$(call print_success,Update complete!)

clean: ## 🧹 Clean temporary files
	$(call print_status,Cleaning temporary files...)
	@rm -rf logs/ dev/temp/* __pycache__/ **/__pycache__/ *.pyc **/*.pyc 2>/dev/null || true
	$(call print_success,Cleanup complete!)

test: ## 🧪 Run test suite
	$(call print_status,Running tests...)
	@if [ -d "$(VENV_PATH)" ]; then \
		. $(VENV_PATH)/bin/activate && python -m pytest; \
	else \
		$(call print_error,Virtual environment not found); \
		echo -e "$(YELLOW)💡 Run 'make install-dev' first$(NC)"; \
		exit 1; \
	fi

# ===========================================
# 🔧 Helper Functions
# ===========================================
define check_prerequisites
	@if ! command -v python3 >/dev/null 2>&1; then \
		$(call print_error,Python 3 not found); \
		exit 1; \
	fi
	@if ! command -v uv >/dev/null 2>&1; then \
		$(call print_status,Installing uv...); \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
endef

define setup_python_env
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_status,Creating virtual environment...); \
		python3 -m venv $(VENV_PATH); \
	fi
	@$(call print_status,Installing dependencies with uv...)
	@. $(VENV_PATH)/bin/activate && uv sync
endef

define create_systemd_service
	@$(call print_status,Creating systemd service...)
	@sudo printf '[Unit]\nDescription=Automagik Agents Service\nAfter=network.target\n\n[Service]\nType=simple\nUser=%s\nWorkingDirectory=%s\nEnvironment=PATH=%s/bin\nExecStart=%s/bin/python -m src\nRestart=always\nRestartSec=10\n\n[Install]\nWantedBy=multi-user.target\n' \
		"$(shell whoami)" "$(PROJECT_ROOT)" "$(VENV_PATH)" "$(VENV_PATH)" > /etc/systemd/system/automagik-agents.service
endef

define show_systemd_status
	@if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		pid=$$(systemctl show automagik-agents --property=MainPID --value 2>/dev/null); \
		port=$$(ss -tlnp | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		printf "$(PURPLE)│$(NC) %-23s $(PURPLE)│$(NC) $(GREEN)%-8s$(NC) $(PURPLE)│$(NC) %-7s $(PURPLE)│$(NC) %-8s $(PURPLE)│$(NC)\n" \
			"systemd-service" "running" "$${port:-8881}" "$$pid"; \
	else \
		printf "$(PURPLE)│$(NC) %-23s $(PURPLE)│$(NC) $(YELLOW)%-8s$(NC) $(PURPLE)│$(NC) %-7s $(PURPLE)│$(NC) %-8s $(PURPLE)│$(NC)\n" \
			"systemd-service" "stopped" "-" "-"; \
	fi
endef

define show_docker_status
	@containers=$$(docker ps --filter "name=automagik-agents" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null); \
	if [ -n "$$containers" ]; then \
		echo "$$containers" | while IFS=$$'\t' read -r name status ports; do \
			port=$$(echo "$$ports" | grep -o '[0-9]*->[0-9]*' | head -1 | cut -d'>' -f2); \
			container_id=$$(docker ps --format "{{.ID}}" --filter "name=$$name" | head -c 6); \
			printf "$(PURPLE)│$(NC) %-23s $(PURPLE)│$(NC) $(GREEN)%-8s$(NC) $(PURPLE)│$(NC) %-7s $(PURPLE)│$(NC) %-8s $(PURPLE)│$(NC)\n" \
				"$$name" "running" "$${port:-8881}" "$$container_id"; \
		done; \
	fi
endef

define show_local_status
	@if pgrep -f "python.*src" >/dev/null 2>&1; then \
		pid=$$(pgrep -f "python.*src"); \
		port=$$(ss -tlnp | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		printf "$(PURPLE)│$(NC) %-23s $(PURPLE)│$(NC) $(GREEN)%-8s$(NC) $(PURPLE)│$(NC) %-7s $(PURPLE)│$(NC) %-8s $(PURPLE)│$(NC)\n" \
			"local-process" "running" "$${port:-8881}" "$$pid"; \
	fi
endef

define check_health
	@healthy=0; \
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) Systemd service: running$(NC)"; \
		healthy=1; \
	fi; \
	if docker ps --filter "name=automagik-agents" --format "{{.Names}}" | grep -q automagik; then \
		echo -e "$(GREEN)$(CHECKMARK) Docker containers: running$(NC)"; \
		healthy=1; \
	fi; \
	if [ $$healthy -eq 0 ]; then \
		echo -e "$(YELLOW)$(WARNING) No services running$(NC)"; \
	fi; \
	if curl -s http://localhost:8881/health >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) API health check: passed$(NC)"; \
	elif curl -s http://localhost:18881/health >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) API health check: passed (prod)$(NC)"; \
		else \
		echo -e "$(YELLOW)$(WARNING) API health check: failed$(NC)"; \
	fi
endef 

# ===========================================
# 🧹 Phony Targets
# ===========================================
.PHONY: help install install-dev install-docker install-prod
.PHONY: dev docker prod stop stop-prod stop-all restart status logs health
.PHONY: update clean test