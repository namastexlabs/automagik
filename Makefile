                                                         
#                                                                        
# ===========================================
# 🪄 Automagik Agents - Streamlined Makefile
# ===========================================

.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash

# ===========================================
# 🎨 Colors & Symbols
# ===========================================
FONT_RED := $(shell tput setaf 1)
FONT_GREEN := $(shell tput setaf 2)
FONT_YELLOW := $(shell tput setaf 3)
FONT_BLUE := $(shell tput setaf 4)
FONT_PURPLE := $(shell tput setaf 5)
FONT_CYAN := $(shell tput setaf 6)
FONT_GRAY := $(shell tput setaf 7)
FONT_BLACK := $(shell tput setaf 8)
FONT_BOLD := $(shell tput bold)
FONT_RESET := $(shell tput sgr0)
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
	echo -e "$(FONT_PURPLE)🪄 $(1)$(FONT_RESET)"
endef

define print_success
	echo -e "$(FONT_GREEN)$(CHECKMARK) $(1)$(FONT_RESET)"
endef

define print_warning
	echo -e "$(FONT_YELLOW)$(WARNING) $(1)$(FONT_RESET)"
endef

define print_error
	echo -e "$(FONT_RED)$(ERROR) $(1)$(FONT_RESET)"
endef

define print_success_with_logo
	echo -e "$(FONT_GREEN)$(CHECKMARK) $(1)$(FONT_RESET)"; \
	$(call show_automagik_logo)
endef

define show_nmstx_logo
	echo ""; \
	echo -e "$(FONT_PURPLE)  :*@@@@*.     :=@@@-%@@@%=          :-@@@%* :*@@@@@@@#-:#@@@@@@@@@@@*-           -#@@@%=   $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@@@#-    :=@@@-%@@@@#=        :-@@@@%--@@@@@%@@@@%-============-.          -@@@@*=    $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@@@@#=   :=@@@-%@@@@@*-      .-@@@@@%-#@@@*  .-%@%+=              :+@@@@*.=@@@@*.     $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@#@@@%*  :=@@@-%@@@@@@*-     -%@@@@@%-#@@@*                        .-@@@@%@@@%+       $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@--@@@@*::=@@@-%@@@%@@@*:   -#@@@@@@%--@@@@@%%#+:     :*@@@*.        -*@@@@@*=        $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@*.-%@@@#:=@@@-%@@@-#@@@*. -*@@@=+@@%* :-@@@@@@@@#-   :*@@@*.        .=@@@@@*.        $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@*. -#@@@#+@@@-%@@@=-#@@@+-+@@@*-+@@%*      .-#@@@*:  :*@@@*.       -*@@@@@@@*-       $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  :*@@@*.  :=@@@@@@@-%@@@*.-@@@%*@@@*--+@@%*       .-@@@**  :*@@@*.      -@@@@#-#@@@%=      $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)            .-@@@@@@-%@@@*..-@@@@@@*=             .=%@@@*.  :*@@@*.    .-@@@@*. .:==-::   $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)              -#@@@@-%@@@*. .-@@@@#=             -+@@@@*:   :*@@@*.   -+@@@%+               $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)               :=+++:=+++-                       ::=-:      .-+++-   :=+++=:                $(FONT_RESET)"; \
	echo ""
endef

define show_automagik_logo
	echo ""; \
	echo -e "$(FONT_PURPLE)                                                                                            $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)                                                                                            $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)     -+*         -=@%*@@@@@@*  -#@@@%*  =@@*      -%@#+   -*       +%@@@@*-%@*-@@*  -+@@*   $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)     =@#*  -@@*  -=@%+@@@@@@*-%@@#%*%@@+=@@@*    -+@@#+  -@@*   -#@@%%@@@*-%@+-@@* -@@#*    $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)    -%@@#* -@@*  -=@@* -@%* -@@**   --@@=@@@@*  -+@@@#+ -#@@%* -*@%*-@@@@*-%@+:@@+#@@*      $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)   -#@+%@* -@@*  -=@@* -@%* -@@*-+@#*-%@+@@=@@* +@%#@#+ =@##@* -%@#*-@@@@*-%@+-@@@@@*       $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  -*@#==@@*-@@*  -+@%* -@%* -%@#*   -+@@=@@++@%-@@=*@#=-@@*-@@*:+@@*  -%@*-%@+-@@#*@@**     $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE)  -@@* -+@%-+@@@@@@@*  -@%*  -#@@@@%@@%+=@@+-=@@@*    -%@*  -@@*-*@@@@%@@*#@@#=%*  -%@@*    $(FONT_RESET)"; \
	echo -e "$(FONT_PURPLE) -@@*+  -%@*  -#@%+    -@%+     =#@@*   =@@+          +@%+  -#@#   -*%@@@*@@@@%+     =@@+   $(FONT_RESET)"; \
	echo ""
endef

define check_docker
	if ! command -v docker >/dev/null 2>&1; then \
		$(call print_error,Docker not found); \
		echo -e "$(FONT_YELLOW)💡 Install Docker: https://docs.docker.com/get-docker/$(FONT_RESET)"; \
		exit 1; \
	fi; \
	if ! docker info >/dev/null 2>&1; then \
		$(call print_error,Docker daemon not running); \
		echo -e "$(FONT_YELLOW)💡 Start Docker service$(FONT_RESET)"; \
		exit 1; \
	fi
endef

define check_env_file
	if [ ! -f ".env" ]; then \
		$(call print_warning,.env file not found); \
		echo -e "$(FONT_CYAN)Copying .env.example to .env...$(FONT_RESET)"; \
		cp .env.example .env; \
		$(call print_success,.env created from example); \
		echo -e "$(FONT_YELLOW)💡 Edit .env and add your API keys$(FONT_RESET)"; \
	fi
endef

define detect_graphiti_profile
	echo ""
endef

define detect_database_type
	if [ -f ".env" ]; then \
		db_type=$$(grep "^DATABASE_TYPE=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]'); \
		if [ "$$db_type" = "postgresql" ]; then \
			echo "postgresql"; \
		else \
			echo "sqlite"; \
		fi; \
	else \
		echo "sqlite"; \
	fi
endef

# ===========================================
# 📋 Help System
# ===========================================
.PHONY: help
help: ## 🪄 Show this help message
	@$(call show_nmstx_logo)
	@echo -e "$(FONT_BOLD)$(FONT_CYAN)Welcome to Automagik Agents$(FONT_RESET) - $(FONT_GRAY)AI Agents from Ideas to Production in Minutes$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_YELLOW)🏢 Built by$(FONT_RESET) $(FONT_BOLD)Namastex Labs$(FONT_RESET) | $(FONT_YELLOW)📄 MIT Licensed$(FONT_RESET) | $(FONT_YELLOW)🌟 Open Source Forever$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)📦 GitHub:$(FONT_RESET) $(FONT_BOLD)https://github.com/namastex-labs/automagik-agents$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_PURPLE)✨ \"Where production-ready agents happen automagikally - no spells required, just good engineering\"$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_PURPLE)🪄 Automagik Agents - Streamlined Commands$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_CYAN)🚀 Installation:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)install$(FONT_RESET)         Install development environment (uv sync) - uses SQLite by default"
	@echo -e "  $(FONT_PURPLE)install-service$(FONT_RESET) Install as systemd service with optional dependencies"
	@echo -e "  $(FONT_PURPLE)install-deps$(FONT_RESET)    Install optional database dependencies (PostgreSQL)"
	@echo -e "  $(FONT_PURPLE)install-docker$(FONT_RESET)  Install Docker development stack"
	@echo -e "  $(FONT_PURPLE)install-prod$(FONT_RESET)    Install production Docker stack"
	@echo ""
	@echo -e "$(FONT_CYAN)🎛️ Service Management:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)dev$(FONT_RESET)             Start development mode (local Python)"
	@echo -e "  $(FONT_PURPLE)run$(FONT_RESET)             Run development server with hot reload"
	@echo -e "  $(FONT_PURPLE)docker$(FONT_RESET)          Start Docker development stack"
	@echo -e "  $(FONT_PURPLE)prod$(FONT_RESET)            Start production Docker stack"
	@echo -e "  $(FONT_PURPLE)start-service$(FONT_RESET)   Start systemd service and show recent logs"
	@echo -e "  $(FONT_PURPLE)stop$(FONT_RESET)            Stop development automagik-agents container only"
	@echo -e "  $(FONT_PURPLE)stop-service$(FONT_RESET)    Stop systemd service"
	@echo -e "  $(FONT_PURPLE)stop-prod$(FONT_RESET)       Stop production automagik-agents container only"
	@echo -e "  $(FONT_PURPLE)stop-all$(FONT_RESET)        Stop all services (DB, etc.)"
	@echo -e "  $(FONT_PURPLE)status$(FONT_RESET)          Show service status"
	@echo ""
	@echo -e "$(FONT_CYAN)📋 Logs & Monitoring:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)logs$(FONT_RESET)            Show last 100 log lines"
	@echo -e "  $(FONT_PURPLE)logs N=50$(FONT_RESET)       Show last N log lines"
	@echo -e "  $(FONT_PURPLE)logs FOLLOW=1$(FONT_RESET)   Follow logs in real-time"
	@echo -e "  $(FONT_PURPLE)health$(FONT_RESET)          Check service health"
	@echo ""
	@echo -e "$(FONT_CYAN)🔄 Maintenance:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)update$(FONT_RESET)          Update and restart services"
	@echo -e "  $(FONT_PURPLE)clean$(FONT_RESET)           Clean temporary files"
	@echo -e "  $(FONT_PURPLE)test$(FONT_RESET)            Run test suite"
	@echo ""
	@echo -e "$(FONT_YELLOW)💡 SQLite is used by default. PostgreSQL is optional$(FONT_RESET)"
	@echo ""

print-test: ## 🎨 Test color system
	@printf "$(FONT_RED)red$(FONT_RESET)\n"
	@printf "$(FONT_GREEN)green$(FONT_RESET)\n"
	@printf "$(FONT_YELLOW)yellow$(FONT_RESET)\n"
	@printf "$(FONT_BLUE)blue$(FONT_RESET)\n"
	@printf "$(FONT_PURPLE)purple$(FONT_RESET)\n"
	@printf "$(FONT_CYAN)cyan$(FONT_RESET)\n"
	@printf "$(FONT_GRAY)gray$(FONT_RESET)\n"
	@printf "$(FONT_BLACK)black$(FONT_RESET)\n"
	@printf "$(FONT_BOLD)bold$(FONT_RESET)\n"

# ===========================================
# 🚀 Installation Targets
# ===========================================
.PHONY: install install-service install-deps install-docker install-prod
install: ## 🛠️ Install development environment
	@$(call print_status,Installing development environment...)
	@$(call check_prerequisites)
	@$(call setup_python_env)
	@$(call check_env_file)
	@$(call print_success_with_logo,Development environment ready!)

install-service: ## ⚙️ Install as systemd service with optional dependencies
	@$(call print_status,Installing Automagik Agents systemd service...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_warning,Virtual environment not found - creating it now...); \
		$(MAKE) install; \
	fi
	@$(call check_env_file)
	@$(call create_systemd_service)
	@$(call print_status,Reloading systemd and enabling service...)
	@sudo systemctl daemon-reload
	@sudo systemctl enable automagik-agents
	@$(call print_success_with_logo,Systemd service installed!)
	@echo -e "$(FONT_CYAN)💡 Start with: sudo systemctl start automagik-agents$(FONT_RESET)"

install-deps: ## 🗄️ Install database dependencies (PostgreSQL - optional for SQLite)
	@$(call print_status,Installing database dependencies...)
	@$(call check_docker)
	@$(call check_env_file)
	@db_type=$$($(call detect_database_type)); \
	if [ "$$db_type" = "postgresql" ]; then \
		$(call print_status,Database type: PostgreSQL - starting container...); \
		$(call print_status,Stopping any existing containers...); \
		$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env stop 2>/dev/null || true; \
		$(call print_status,Starting PostgreSQL container...); \
		$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env up -d --force-recreate automagik-agents-db; \
		$(call print_status,Waiting for PostgreSQL to be ready...); \
		sleep 5; \
		$(call check_postgres_ready); \
		echo -e "$(FONT_GREEN)$(CHECKMARK) PostgreSQL started successfully!$(FONT_RESET)"; \
	else \
		$(call print_status,Database type: SQLite - no container needed); \
		echo -e "$(FONT_GREEN)$(CHECKMARK) SQLite configured - database will be created automatically$(FONT_RESET)"; \
	fi
	@$(call print_success_with_logo,Database dependencies setup complete!)

install-docker: ## 🐳 Install Docker development stack
	@$(call print_status,Installing Docker development stack...)
	@$(call check_docker)
	@$(call check_env_file)
	@$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env build
	@$(call print_status,Starting Docker development stack...)
	@$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env up -d
	@$(call print_success_with_logo,Docker development stack ready!)

install-prod: ## 🏭 Install production Docker stack
	@$(call print_status,Installing production Docker stack...)
	@$(call check_docker)
	@if [ ! -f ".env.prod" ]; then \
		$(call print_error,.env.prod file not found); \
		echo -e "$(FONT_YELLOW)💡 Create .env.prod for production$(FONT_RESET)"; \
		exit 1; \
	fi
	@$(call print_status,Building production containers...)
	@env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) build
	@$(call print_status,Starting production Docker stack...)
	@env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) up -d
	@$(call print_success_with_logo,Production Docker stack ready!)

# ===========================================
# 🎛️ Service Management
# ===========================================
.PHONY: dev docker prod stop stop-prod stop-all run start-service stop-service status
dev: ## 🛠️ Start development mode
	$(call print_status,Starting development mode...)
	@$(call check_env_file)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found); \
		echo -e "$(FONT_YELLOW)💡 Run 'make install' first$(FONT_RESET)"; \
		exit 1; \
	fi
	@$(call print_status,Starting with uv run...)
	@AM_FORCE_DEV_ENV=1 uv run python -m src

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

run: ## 🚀 Run development server with hot reload
	$(call print_status,Starting development server with hot reload...)
	@$(call check_env_file)
	@echo -e "$(FONT_YELLOW)💡 Press Ctrl+C to stop the server$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)🧹 Nuclear cleanup of any zombie processes...$(FONT_RESET)"
	@ps aux | grep -E "(python.*src|uv run|uvicorn|multiprocessing)" | grep -v grep | awk '{print $$2}' | xargs -r kill -9 2>/dev/null || true
	@sleep 1
	@echo -e "$(FONT_PURPLE)🚀 Starting server...$(FONT_RESET)"
	@AM_FORCE_DEV_ENV=1 uv run python -m src --reload

start-service: ## 🔧 Start systemd service and show recent logs
	$(call print_status,Starting systemd service...)
	@if systemctl is-enabled automagik-agents >/dev/null 2>&1; then \
		sudo systemctl start automagik-agents; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Systemd service started!$(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)🪄 Recent logs:$(FONT_RESET)"; \
		journalctl -u automagik-agents -n 20 --no-pager | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) Systemd service not installed$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)💡 Run 'make install-service' first$(FONT_RESET)"; \
	fi

stop-service: ## 🛑 Stop systemd service
	$(call print_status,Stopping systemd service...)
	@if systemctl is-enabled automagik-agents >/dev/null 2>&1; then \
		sudo systemctl stop automagik-agents; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Systemd service stopped!$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) Systemd service not installed$(FONT_RESET)"; \
	fi

status: ## 📊 Show service status
	$(call print_status,Service Status)
	@echo ""
	@echo -e "$(FONT_PURPLE)┌─────────────────────────┬──────────┬─────────┬──────────┐$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)│ Service                 │ Status   │ Port    │ PID      │$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)├─────────────────────────┼──────────┼─────────┼──────────┤$(FONT_RESET)"
	@$(call show_systemd_status)
	@$(call show_docker_status)
	@$(call show_local_status)
	@echo -e "$(FONT_PURPLE)└─────────────────────────┴──────────┴─────────┴──────────┘$(FONT_RESET)"

# ===========================================
# 📋 Logs & Monitoring
# ===========================================
.PHONY: logs health
logs: ## 📄 View logs (use N=lines, FOLLOW=1 for tail -f)
	@if [ "$(FOLLOW)" = "1" ]; then \
		echo -e "$(FONT_PURPLE)🪄 Following logs - Press Ctrl+C to stop$(FONT_RESET)"; \
		if systemctl is-active automagik-agents >/dev/null 2>&1; then \
			journalctl -u automagik-agents -f --no-pager | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1 | grep -q automagik; then \
			container=$$(docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1); \
			docker logs -f $$container 2>&1 | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif [ -f "logs/automagik.log" ]; then \
			tail -f logs/automagik.log | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		else \
			echo -e "$(FONT_YELLOW)⚠️ No log sources found to follow$(FONT_RESET)"; \
		fi; \
	else \
		echo -e "$(FONT_PURPLE)🪄 Showing last $(N) log lines$(FONT_RESET)"; \
		if systemctl is-active automagik-agents >/dev/null 2>&1; then \
			journalctl -u automagik-agents -n $(N) --no-pager | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1 | grep -q automagik; then \
			container=$$(docker ps --filter "name=automagik-agents" --format "{{.Names}}" | head -1); \
			docker logs --tail $(N) $$container 2>&1 | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		elif [ -f "logs/automagik.log" ]; then \
			tail -n $(N) logs/automagik.log | sed -e 's/ERROR/\x1b[31mERROR\x1b[0m/g' -e 's/WARN/\x1b[33mWARN\x1b[0m/g' -e 's/INFO/\x1b[32mINFO\x1b[0m/g' -e 's/DEBUG/\x1b[36mDEBUG\x1b[0m/g' -e 's/📝/\x1b[35m📝\x1b[0m/g' -e 's/✅/\x1b[32m✅\x1b[0m/g' -e 's/❌/\x1b[31m❌\x1b[0m/g' -e 's/⚠️/\x1b[33m⚠️\x1b[0m/g'; \
		else \
			echo -e "$(FONT_YELLOW)⚠️ No log sources found$(FONT_RESET)"; \
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
		$(MAKE) install && sudo systemctl start automagik-agents; \
	elif docker ps -a --filter "name=automagik-agents-prod" --format "{{.Names}}" | grep -q prod; then \
		$(MAKE) install-prod; \
	elif docker ps -a --filter "name=automagik-agents-dev" --format "{{.Names}}" | grep -q dev; then \
		$(MAKE) install-docker; \
	else \
		$(call print_warning,No previous installation detected); \
	fi
	$(call print_success_with_logo,Update complete!)

clean: ## 🧹 Clean temporary files
	$(call print_status,Cleaning temporary files...)
	@rm -rf logs/ 2>/dev/null || true
	@rm -rf dev/temp/* 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -type f -delete 2>/dev/null || true
	@find . -name "*.pyo" -type f -delete 2>/dev/null || true
	$(call print_success,Cleanup complete!)

test: ## 🧪 Run test suite
	$(call print_status,Running tests...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found); \
		echo -e "$(FONT_YELLOW)💡 Run 'make install' first$(FONT_RESET)"; \
		exit 1; \
	fi
	@uv run python -m pytest

# ===========================================
# 🔧 Helper Functions
# ===========================================

define check_postgres_ready
	@max_attempts=12; \
	attempt=1; \
	while [ $$attempt -le $$max_attempts ]; do \
		if docker exec automagik-agents-db pg_isready -U postgres >/dev/null 2>&1; then \
			echo -e "$(FONT_GREEN)$(CHECKMARK) PostgreSQL is ready!$(FONT_RESET)"; \
			break; \
		else \
			echo -n "$(FONT_YELLOW).$(FONT_RESET)"; \
			sleep 5; \
			attempt=$$((attempt + 1)); \
		fi; \
	done; \
	if [ $$attempt -gt $$max_attempts ]; then \
		echo -e "$(FONT_RED)$(ERROR) PostgreSQL failed to start within 60 seconds$(FONT_RESET)"; \
		exit 1; \
	fi
endef

define check_prerequisites
	if ! command -v python3 >/dev/null 2>&1; then \
		$(call print_error,Python 3 not found); \
		exit 1; \
	fi; \
	if ! command -v uv >/dev/null 2>&1; then \
		if [ -f "$$HOME/.local/bin/uv" ]; then \
			export PATH="$$HOME/.local/bin:$$PATH"; \
			$(call print_status,Found uv in $$HOME/.local/bin); \
		else \
			$(call print_status,Installing uv...); \
			curl -LsSf https://astral.sh/uv/install.sh | sh; \
			export PATH="$$HOME/.local/bin:$$PATH"; \
			$(call print_success,uv installed successfully); \
		fi; \
	else \
		$(call print_status,uv is already available in PATH); \
	fi
endef

define setup_python_env
	$(call print_status,Installing dependencies with uv...); \
	if command -v uv >/dev/null 2>&1; then \
		uv sync; \
	elif [ -f "$$HOME/.local/bin/uv" ]; then \
		$$HOME/.local/bin/uv sync; \
	else \
		$(call print_error,uv not found - please run 'make install' without sudo first); \
		exit 1; \
	fi
endef

define create_systemd_service
	$(call print_status,Creating systemd service...); \
	printf '[Unit]\nDescription=Automagik Agents Service\nAfter=network.target\n\n[Service]\nType=simple\nUser=%s\nWorkingDirectory=%s\nEnvironment=PATH=%s/bin:%s/.local/bin:/usr/local/bin:/usr/bin:/bin\nExecStart=%s/bin/python -m src\nRestart=always\nRestartSec=10\n\n[Install]\nWantedBy=multi-user.target\n' \
		"$(shell whoami)" "$(PROJECT_ROOT)" "$(VENV_PATH)" "$(HOME)" "$(VENV_PATH)" | sudo tee /etc/systemd/system/automagik-agents.service > /dev/null
endef

define show_systemd_status
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		pid=$$(systemctl show automagik-agents --property=MainPID --value 2>/dev/null); \
		port=$$(ss -tlnp | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_GREEN)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"systemd-service" "running" "$${port:-8881}" "$$pid"; \
	else \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_YELLOW)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"systemd-service" "stopped" "-" "-"; \
	fi
endef

define show_docker_status
	containers=$$(docker ps --filter "name=automagik-agents" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null); \
	if [ -n "$$containers" ]; then \
		echo "$$containers" | while IFS=$$'\t' read -r name status ports; do \
			port=$$(echo "$$ports" | grep -o '[0-9]*->[0-9]*' | head -1 | cut -d'>' -f2); \
			container_id=$$(docker ps --format "{{.ID}}" --filter "name=$$name" | head -c 6); \
			printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_GREEN)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
				"$$name" "running" "$${port:-8881}" "$$container_id"; \
		done; \
	fi
endef

define show_local_status
	if pgrep -f "python.*src" >/dev/null 2>&1; then \
		pid=$$(pgrep -f "python.*src"); \
		port=$$(ss -tlnp | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_GREEN)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"local-process" "running" "$${port:-8881}" "$$pid"; \
	fi
endef

define check_health
	@healthy=0; \
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Systemd service: running$(FONT_RESET)"; \
		healthy=1; \
	fi; \
	if docker ps --filter "name=automagik-agents" --format "{{.Names}}" | grep -q automagik; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Docker containers: running$(FONT_RESET)"; \
		healthy=1; \
	fi; \
	if [ $$healthy -eq 0 ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) No services running$(FONT_RESET)"; \
	fi; \
	if curl -s http://localhost:8881/health >/dev/null 2>&1; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) API health check: passed$(FONT_RESET)"; \
	elif curl -s http://localhost:18881/health >/dev/null 2>&1; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) API health check: passed (prod)$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) API health check: failed$(FONT_RESET)"; \
	fi; \
	db_type=$$($(call detect_database_type)); \
	if [ "$$db_type" = "postgresql" ]; then \
		if docker ps --filter "name=automagik-agents-db" --format "{{.Names}}" | grep -q automagik-agents-db; then \
			if docker exec automagik-agents-db pg_isready -U postgres >/dev/null 2>&1; then \
				echo -e "$(FONT_GREEN)$(CHECKMARK) PostgreSQL database: healthy$(FONT_RESET)"; \
			else \
				echo -e "$(FONT_YELLOW)$(WARNING) PostgreSQL database: not ready$(FONT_RESET)"; \
			fi; \
		else \
			echo -e "$(FONT_YELLOW)$(WARNING) PostgreSQL container: not running$(FONT_RESET)"; \
		fi; \
	else \
		echo -e "$(FONT_GREEN)$(CHECKMARK) SQLite database: configured$(FONT_RESET)"; \
	fi
endef

# ===========================================
# 🧹 Phony Targets
# ===========================================
.PHONY: help print-test install install-service install-deps install-docker install-prod
.PHONY: dev docker prod stop stop-prod stop-all run start-service stop-service status logs health
.PHONY: update clean test