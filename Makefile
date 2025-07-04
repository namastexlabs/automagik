                                                         
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

# UV command
UV := uv

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
	[ -z "$$AUTOMAGIK_QUIET_LOGO" ] && { \
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
		echo ""; \
	} || true
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

install-service: ## ⚙️ Install as local PM2 service
	@$(call print_status,Installing Automagik Agents as local PM2 service...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_warning,Virtual environment not found - creating it now...); \
		$(MAKE) install; \
	fi
	@$(call check_env_file)
	@$(MAKE) start-local
	@$(call print_success_with_logo,Local PM2 service installed!)
	@echo -e "$(FONT_CYAN)💡 Service is now managed by local PM2$(FONT_RESET)"

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

install-pip: ## 📦 Install package via pip (editable mode)
	@$(call print_status,Installing automagik package via pip...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_warning,Virtual environment not found - creating it now...); \
		$(UV) venv $(VENV_PATH); \
		$(call print_success,Virtual environment created); \
	fi
	@$(call print_status,Installing package in editable mode...)
	@$(VENV_PATH)/bin/pip install -e .
	@$(call print_success_with_logo,Package installed successfully!)
	@echo -e "$(FONT_CYAN)💡 You can now use 'automagik' command$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)💡 Start the API server with: automagik-server$(FONT_RESET)"

build-pip: ## 📦 Build pip package for distribution
	@$(call print_status,Building pip package...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found); \
		echo -e "$(FONT_YELLOW)💡 Run 'make install' first$(FONT_RESET)"; \
		exit 1; \
	fi
	@$(VENV_PATH)/bin/pip install build
	@$(VENV_PATH)/bin/python -m build
	@$(call print_success,Package built successfully!)
	@echo -e "$(FONT_CYAN)📦 Distribution files created in ./dist/$(FONT_RESET)"

publish-pip: ## 📤 Publish package to PyPI
	@$(call print_status,Publishing package to PyPI...)
	@if [ ! -d "dist" ]; then \
		$(call print_error,No distribution files found); \
		echo -e "$(FONT_YELLOW)💡 Run 'make build-pip' first$(FONT_RESET)"; \
		exit 1; \
	fi
	@$(VENV_PATH)/bin/pip install twine
	@$(VENV_PATH)/bin/twine upload dist/*
	@$(call print_success,Package published to PyPI!)

# ===========================================
# 🎛️ Service Management
# ===========================================
.PHONY: dev docker prod stop stop-prod stop-all start-service stop-service restart-service uninstall-service status
dev: ## 🛠️ Start development mode with hot reload
	$(call print_status,Starting development mode with hot reload...)
	@$(call check_env_file)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found); \
		echo -e "$(FONT_YELLOW)💡 Run 'make install' first$(FONT_RESET)"; \
		exit 1; \
	fi
	@echo -e "$(FONT_YELLOW)💡 Press Ctrl+C to stop the server$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)🧹 Nuclear cleanup of any zombie processes...$(FONT_RESET)"
	@ps aux | grep -E "(python.*automagik|uv run|uvicorn|multiprocessing)" | grep -v grep | awk '{print $$2}' | xargs -r kill -9 2>/dev/null || true
	@sleep 1
	@echo -e "$(FONT_PURPLE)🚀 Starting server...$(FONT_RESET)"
	@uv run python -m automagik --reload

docker: ## 🐳 Start Docker development stack
	@$(call print_status,Starting Docker development stack...)
	@$(call check_docker)
	@$(call check_env_file)
	$(call print_status,Starting services...); \
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env up -d
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
	@pm2 stop am-agents-labs 2>/dev/null || true
	@docker stop automagik-agents-dev 2>/dev/null || true
	@pkill -f "python.*automagik" 2>/dev/null || true
	$(call print_success,Development automagik-agents stopped!)

stop-prod: ## 🛑 Stop production automagik-agents container only
	$(call print_status,Stopping production automagik-agents container...)
	@docker stop automagik-agents-prod 2>/dev/null || true
	$(call print_success,Production automagik-agents stopped!)

stop-all: ## 🛑 Stop all services (preserves containers)
	$(call print_status,Stopping all services...)
	@pm2 stop am-agents-labs 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV) --env-file .env stop 2>/dev/null || true
	@if [ -f ".env.prod" ]; then \
		env $(shell cat .env.prod | grep -v '^#' | xargs) $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) stop 2>/dev/null || true; \
	else \
		$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_PROD) --env-file .env stop 2>/dev/null || true; \
	fi
	@pkill -f "python.*automagik" 2>/dev/null || true
	$(call print_success,All services stopped!)


start-service: ## 🔧 Start local PM2 service
	@$(MAKE) start-local

stop-service: ## 🛑 Stop local PM2 service
	@$(MAKE) stop-local

restart-service: ## 🔄 Restart local PM2 service
	@$(MAKE) restart-local

uninstall-service: ## 🗑️ Uninstall local PM2 service
	$(call print_status,Uninstalling local PM2 service...)
	@$(call check_pm2)
	@pm2 delete am-agents-labs 2>/dev/null || true
	@pm2 save --force
	@echo -e "$(FONT_GREEN)$(CHECKMARK) Local PM2 service uninstalled!$(FONT_RESET)"

status: ## 📊 Show service status
	$(call print_status,Service Status)
	@echo ""
	@echo -e "$(FONT_PURPLE)┌─────────────────────────┬──────────┬─────────┬──────────┐$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)│ Service                 │ Status   │ Port    │ PID      │$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)├─────────────────────────┼──────────┼─────────┼──────────┤$(FONT_RESET)"
	@$(call show_pm2_status)
	@$(call show_docker_status)
	@$(call show_local_status)
	@echo -e "$(FONT_PURPLE)└─────────────────────────┴──────────┴─────────┴──────────┘$(FONT_RESET)"

# ===========================================
# 🔧 Local PM2 Management (Standalone Mode)
# ===========================================
.PHONY: start-local stop-local restart-local

start-local: ## 🚀 Start service using local PM2 ecosystem
	$(call print_status,Starting am-agents-labs with local PM2...)
	@$(call check_pm2)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found); \
		echo -e "$(FONT_YELLOW)💡 Run 'make install' first$(FONT_RESET)"; \
		exit 1; \
	fi
	@$(call check_env_file)
	@pm2 start ecosystem.config.js
	@$(call print_success,Service started with local PM2!)

stop-local: ## 🛑 Stop service using local PM2 ecosystem
	$(call print_status,Stopping am-agents-labs with local PM2...)
	@$(call check_pm2)
	@pm2 stop am-agents-labs 2>/dev/null || true
	@$(call print_success,Service stopped!)

restart-local: ## 🔄 Restart service using local PM2 ecosystem
	$(call print_status,Restarting am-agents-labs with local PM2...)
	@$(call check_pm2)
	@pm2 restart am-agents-labs 2>/dev/null || pm2 start ecosystem.config.js
	@$(call print_success,Service restarted!)

# ===========================================
# 📋 Logs & Monitoring
# ===========================================
.PHONY: logs health logs-follow
logs: ## 📄 View logs (use N=lines)
	@echo -e "$(FONT_PURPLE)🪄 Showing last $(N) log lines$(FONT_RESET)"
	@pm2 logs am-agents-labs --lines $(N) --nostream 2>/dev/null || echo -e "$(FONT_YELLOW)⚠️ Service not found or not running$(FONT_RESET)"

logs-follow: ## 📄 Follow logs in real-time
	@echo -e "$(FONT_PURPLE)🪄 Following logs - Press Ctrl+C to stop$(FONT_RESET)"
	@pm2 logs am-agents-labs 2>/dev/null || echo -e "$(FONT_YELLOW)⚠️ Service not found or not running$(FONT_RESET)"

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
	@if pm2 list 2>/dev/null | grep -q am-agents-labs; then \
		$(MAKE) install && pm2 restart am-agents-labs; \
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
		if ! uv sync 2>/dev/null; then \
			$(call print_warning,Installation failed - clearing UV cache and retrying...); \
			uv cache clean; \
			uv sync; \
		fi; \
	elif [ -f "$$HOME/.local/bin/uv" ]; then \
		if ! $$HOME/.local/bin/uv sync 2>/dev/null; then \
			$(call print_warning,Installation failed - clearing UV cache and retrying...); \
			$$HOME/.local/bin/uv cache clean; \
			$$HOME/.local/bin/uv sync; \
		fi; \
	else \
		$(call print_error,uv not found - please run 'make install' without sudo first); \
		exit 1; \
	fi
endef

define check_pm2
	@if ! command -v pm2 >/dev/null 2>&1; then \
		$(call print_error,PM2 not found. Install with: npm install -g pm2); \
		exit 1; \
	fi
endef

define show_pm2_status
	if pm2 list 2>/dev/null | grep -q "am-agents-labs.*online"; then \
		pid=$$(pm2 list --no-color 2>/dev/null | awk "/am-agents-labs.*online/ {print \$$10}"); \
		port="8881"; \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_GREEN)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"pm2-service" "running" "$$port" "$$pid"; \
	elif pm2 list 2>/dev/null | grep -q "am-agents-labs"; then \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_YELLOW)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"pm2-service" "stopped" "-" "-"; \
	else \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_RED)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"pm2-service" "not installed" "-" "-"; \
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
	if pgrep -f "python.*automagik" >/dev/null 2>&1; then \
		pid=$$(pgrep -f "python.*automagik"); \
		port=$$(ss -tlnp | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		printf "$(FONT_PURPLE)│$(FONT_RESET) %-23s $(FONT_PURPLE)│$(FONT_RESET) $(FONT_GREEN)%-8s$(FONT_RESET) $(FONT_PURPLE)│$(FONT_RESET) %-7s $(FONT_PURPLE)│$(FONT_RESET) %-8s $(FONT_PURPLE)│$(FONT_RESET)\n" \
			"local-process" "running" "$${port:-8881}" "$$pid"; \
	fi
endef

define check_health
	@healthy=0; \
	if pm2 list 2>/dev/null | grep -q "am-agents-labs.*online"; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) PM2 service: running$(FONT_RESET)"; \
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
# 📦 Build & Publish
# ===========================================
.PHONY: build publish-test publish check-dist check-release clean-build
.PHONY: bump-patch bump-minor bump-major bump-dev publish-dev finalize-version

build: clean-build ## 📦 Build package
	$(call print_status,Building package...)
	@$(UV) build
	$(call print_success,Package built!)

check-dist: ## 🔍 Check package quality
	$(call print_status,Checking package quality...)
	@$(UV) run twine check dist/*

check-release: ## 🔍 Check if ready for release (clean working directory)
	$(call print_status,Checking release readiness...)
	@# Check for uncommitted changes
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo -e "$(FONT_RED)$(ERROR) Uncommitted changes detected!$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Please commit or stash your changes before publishing.$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Run: git status$(FONT_RESET)"; \
		exit 1; \
	fi
	@# Check if on main branch
	@CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$CURRENT_BRANCH" != "main" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Not on main branch (current: $$CURRENT_BRANCH)$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)It's recommended to publish from the main branch.$(FONT_RESET)"; \
		read -p "Continue anyway? [y/N] " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			exit 1; \
		fi; \
	fi
	@# Check if main branch is up to date with origin
	@git fetch origin main --quiet; \
	if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse origin/main)" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Local main branch differs from origin/main$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Consider pulling latest changes or pushing your commits.$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Run: git pull origin main$(FONT_RESET)"; \
		read -p "Continue anyway? [y/N] " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			exit 1; \
		fi; \
	fi
	$(call print_success,Ready for release!)

publish-test: build check-dist ## 🧪 Upload to TestPyPI
	$(call print_status,Publishing to TestPyPI...)
	@if [ -z "$(TESTPYPI_TOKEN)" ]; then \
		$(call print_error,TESTPYPI_TOKEN not set); \
		echo -e "$(FONT_YELLOW)💡 Get your TestPyPI token at: https://test.pypi.org/manage/account/token/$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)💡 Set with: export TESTPYPI_TOKEN=pypi-xxxxx$(FONT_RESET)"; \
		exit 1; \
	fi
	@$(UV) run twine upload --repository testpypi dist/* -u __token__ -p "$(TESTPYPI_TOKEN)"
	$(call print_success,Published to TestPyPI!)

publish: check-release ## 🚀 Create GitHub release (triggers automated PyPI publishing)
	$(call print_status,Creating GitHub release to trigger automated PyPI publishing...)
	@# Get version from pyproject.toml
	@VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	echo -e "$(FONT_CYAN)Publishing version: v$$VERSION$(FONT_RESET)"; \
	if ! git tag | grep -q "^v$$VERSION$$"; then \
		echo -e "$(FONT_CYAN)Creating git tag v$$VERSION$(FONT_RESET)"; \
		git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	fi; \
	echo -e "$(FONT_CYAN)Pushing tag to GitHub$(FONT_RESET)"; \
	git push origin "v$$VERSION"; \
	if command -v gh >/dev/null 2>&1; then \
		echo -e "$(FONT_CYAN)Creating GitHub release$(FONT_RESET)"; \
		gh release create "v$$VERSION" \
			--title "v$$VERSION" \
			--notes "Release v$$VERSION - Automated PyPI publishing via GitHub Actions with Trusted Publisher" \
			--generate-notes || echo -e "$(FONT_YELLOW)$(WARNING) GitHub release creation failed (may already exist)$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) GitHub CLI (gh) not found - creating release manually$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Go to: https://github.com/namastexlabs/am-agents-labs/releases/new$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Tag: v$$VERSION$(FONT_RESET)"; \
	fi; \
	echo -e "$(FONT_PURPLE)🚀 GitHub Actions will now build and publish to PyPI automatically!$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)Monitor progress: https://github.com/namastexlabs/am-agents-labs/actions$(FONT_RESET)"
	$(call print_success,GitHub release created! PyPI publishing in progress...)

publish-github: check-release ## 🚀 Create GitHub release (triggers GitHub Actions for PyPI)
	$(call print_status,Creating GitHub release to trigger automated PyPI publishing...)
	@# Get version from pyproject.toml
	@VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	echo -e "$(FONT_CYAN)Publishing version: v$$VERSION$(FONT_RESET)"; \
	if ! git tag | grep -q "^v$$VERSION$$"; then \
		echo -e "$(FONT_CYAN)Creating git tag v$$VERSION$(FONT_RESET)"; \
		git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	fi; \
	echo -e "$(FONT_CYAN)Pushing tag to GitHub$(FONT_RESET)"; \
	git push origin "v$$VERSION"; \
	if command -v gh >/dev/null 2>&1; then \
		echo -e "$(FONT_CYAN)Creating GitHub release$(FONT_RESET)"; \
		gh release create "v$$VERSION" \
			--title "v$$VERSION" \
			--notes "Release v$$VERSION - Automated PyPI publishing via GitHub Actions with Trusted Publisher" \
			--generate-notes || echo -e "$(FONT_YELLOW)$(WARNING) GitHub release creation failed (may already exist)$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) GitHub CLI (gh) not found - creating release manually$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Go to: https://github.com/namastexlabs/am-agents-labs/releases/new$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Tag: v$$VERSION$(FONT_RESET)"; \
	fi; \
	echo -e "$(FONT_PURPLE)🚀 GitHub Actions will now build and publish to PyPI automatically!$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)Monitor progress: https://github.com/namastexlabs/am-agents-labs/actions$(FONT_RESET)"
	$(call print_success,GitHub release created! PyPI publishing in progress...)

clean-build: ## 🧹 Clean build artifacts
	$(call print_status,Cleaning build artifacts...)
	@rm -rf build dist *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	$(call print_success,Build artifacts cleaned!)

# ===========================================
# 📈 Version Management
# ===========================================
bump-patch: ## 📈 Bump patch version (0.1.0 -> 0.1.1)
	$(call print_status,Bumping patch version...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g'); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version bumped from $$CURRENT_VERSION to $$NEW_VERSION$(FONT_RESET)"

bump-minor: ## 📈 Bump minor version (0.1.0 -> 0.2.0)
	$(call print_status,Bumping minor version...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{$$2 = $$2 + 1; $$3 = 0;} 1' | sed 's/ /./g'); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version bumped from $$CURRENT_VERSION to $$NEW_VERSION$(FONT_RESET)"

bump-major: ## 📈 Bump major version (0.1.0 -> 1.0.0)
	$(call print_status,Bumping major version...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{$$1 = $$1 + 1; $$2 = 0; $$3 = 0;} 1' | sed 's/ /./g'); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version bumped from $$CURRENT_VERSION to $$NEW_VERSION$(FONT_RESET)"

bump-dev: ## 🧪 Create dev version (0.1.2 -> 0.1.2pre1, 0.1.2pre1 -> 0.1.2pre2)
	$(call print_status,Creating dev pre-release version...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	if echo "$$CURRENT_VERSION" | grep -q "pre"; then \
		BASE_VERSION=$$(echo "$$CURRENT_VERSION" | cut -d'p' -f1); \
		PRE_NUM=$$(echo "$$CURRENT_VERSION" | sed 's/.*pre\([0-9]*\)/\1/'); \
		NEW_PRE_NUM=$$((PRE_NUM + 1)); \
		NEW_VERSION="$${BASE_VERSION}pre$${NEW_PRE_NUM}"; \
	else \
		NEW_VERSION="$${CURRENT_VERSION}pre1"; \
	fi; \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Dev version created: $$CURRENT_VERSION → $$NEW_VERSION$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)💡 Ready for: make publish-dev$(FONT_RESET)"

publish-dev: build check-dist ## 🚀 Build and publish dev version to PyPI
	$(call print_status,Publishing dev version to PyPI...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	if ! echo "$$CURRENT_VERSION" | grep -q "pre"; then \
		$(call print_error,Not a dev version! Use 'make bump-dev' first); \
		echo -e "$(FONT_GRAY)Current version: $$CURRENT_VERSION$(FONT_RESET)"; \
		exit 1; \
	fi
	@if [ -z "$(PYPI_TOKEN)" ]; then \
		$(call print_error,PYPI_TOKEN not set); \
		echo -e "$(FONT_YELLOW)💡 Get your PyPI token at: https://pypi.org/manage/account/token/$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)💡 Set with: export PYPI_TOKEN=pypi-xxxxx$(FONT_RESET)"; \
		exit 1; \
	fi
	@echo -e "$(FONT_CYAN)🚀 Publishing $$CURRENT_VERSION to PyPI for beta testing...$(FONT_RESET)"
	@$(UV) run twine upload dist/* -u __token__ -p "$(PYPI_TOKEN)"
	@echo -e "$(FONT_GREEN)✅ Dev version published to PyPI!$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)💡 Users can install with: pip install automagik==$$CURRENT_VERSION$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)💡 Or latest pre-release: pip install --pre automagik$(FONT_RESET)"

finalize-version: ## ✅ Remove 'pre' from version (0.1.2pre3 -> 0.1.2)
	$(call print_status,Finalizing version for release...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	if ! echo "$$CURRENT_VERSION" | grep -q "pre"; then \
		$(call print_error,Not a pre-release version!); \
		echo -e "$(FONT_GRAY)Current version: $$CURRENT_VERSION$(FONT_RESET)"; \
		exit 1; \
	fi; \
	FINAL_VERSION=$$(echo "$$CURRENT_VERSION" | cut -d'p' -f1); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$FINAL_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version finalized: $$CURRENT_VERSION → $$FINAL_VERSION$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)💡 Ready for: make publish$(FONT_RESET)"

# ===========================================
# 🧹 Phony Targets
# ===========================================
.PHONY: help print-test install install-service install-deps install-docker install-prod
.PHONY: dev docker prod stop stop-prod stop-all start-service stop-service status logs health
.PHONY: update clean test build publish-test publish check-dist check-release clean-build
.PHONY: bump-patch bump-minor bump-major bump-dev publish-dev finalize-version