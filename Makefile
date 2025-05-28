# ===========================================
# 🪄 Automagik Agents - Makefile
# ===========================================
# Production-grade AI agent deployment automation
# Designed for AI agents to parse and execute

.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash

# ===========================================
# 🪄 COLORS & STYLING
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
MAGIC := 🪄
SPARKLE := ✨

# ===========================================
# 🪄 CONFIGURATION
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
# 🪄 UTILITY FUNCTIONS
# ===========================================
define print_banner
	@echo ""
	@echo -e "$(BOLD_PURPLE)"
	@echo -e "  ╔════════════════════════════════════════════════════════════════════════════════════╗"
	@echo -e "  ║                                                                                    ║"
	@echo -e "  ║         █▓         ████████▓ ██████▓░░██▓     ██▓   ▓▓     ██████▓▓█▓░██▓ ░██▓     ║"
	@echo -e "  ║        ███▓ ░██▓   ██▓     ▒██▓   ▒██░███▓   ███▓  ▒██▓   ██▓     ██▓▒██ ██▓       ║"
	@echo -e "  ║       ██▓██▓░██▓   ██▓▒██▓ ██▓░██▓ ██░████▓ ████▓  ████▓▒██▓▒████▓██▓▒████▓        ║"
	@echo -e "  ║       ██ ░██▒██▓   ██▓░██▓  ██▓   ███▒█▓░████▓▒█▓░██▓ ██▓ ██▓  ██▓▒█▓▒██░██▓       ║"
	@echo -e "  ║      ██▓  ██▓ █████▓▓  ██▓   ██████▓ ░█▓  ██▓    ██▓   ██  ███████████▓    ██▓     ║"
	@echo -e "  ║                                                                                    ║"
	@echo -e "  ║                      ✨ 🪄 Automagik AI Agents 🪄 ✨                              ║"
	@echo -e "  ║                           by Namastex Labs namastex.ai                             ║"
	@echo -e "  ║                                                                                    ║"
	@echo -e "  ╚════════════════════════════════════════════════════════════════════════════════════╝"
	@echo -e "$(NC)"
	@echo ""
endef

define print_section
	@echo ""
	@echo -e "$(PURPLE)$(1)$(NC)"
	@echo -e "$(PURPLE)$(shell printf '=%.0s' {1..$(shell echo '$(1)' | wc -c)})$(NC)"
endef

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

define check_env_file
	@if [ ! -f "$(1)" ]; then \
		$(call print_error,Environment file $(1) not found); \
		echo -e "$(YELLOW)💡 Copy .env.example to $(1) and configure it$(NC)"; \
		exit 1; \
	fi
endef

define check_venv
	@if [ ! -d "$(VENV_PATH)" ]; then \
		$(call print_error,Virtual environment not found at $(VENV_PATH)); \
		echo -e "$(YELLOW)💡 Run 'make install-dev' to set up the environment$(NC)"; \
		exit 1; \
	fi
endef

define check_docker
	@if ! command -v docker >/dev/null 2>&1; then \
		$(call print_error,Docker not found); \
		echo -e "$(YELLOW)💡 Install Docker first: https://docs.docker.com/get-docker/$(NC)"; \
		exit 1; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		$(call print_error,Docker Compose not found); \
		echo -e "$(YELLOW)💡 Install Docker Compose: https://docs.docker.com/compose/install/$(NC)"; \
		exit 1; \
	fi
endef

define magic_loading
	@echo -ne "$(PURPLE)$(MAGIC) $(1)"; \
	for i in 1 2 3; do \
		echo -ne " $(SPARKLE)"; \
		sleep 0.3; \
	done; \
	echo -e " $(GREEN)$(CHECKMARK)$(NC)"
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
# 🪄 PHONY TARGETS
# ===========================================
.PHONY: help install start stop restart status logs health dev docker prod
.PHONY: install-dev install-docker install-prod clean reset test lint format
.PHONY: db-init db-migrate db-reset docker-build docker-clean
.PHONY: requirements-update venv-create venv-clean check-system
.PHONY: install-prerequisites install-prerequisites-linux install-prerequisites-mac
.PHONY: install-prerequisites-debian install-prerequisites-rhel install-prerequisites-fedora install-prerequisites-arch
.PHONY: install-docker-debian install-docker-rhel install-docker-fedora install-docker-arch
.PHONY: install-uv verify-prerequisites
.PHONY: install-python-env install-service install-postgres install-neo4j install-graphiti
.PHONY: install-database-local check-env-dev check-env-prod verify-docker
.PHONY: venv-create venv-clean requirements-update setup-prod-volumes
.PHONY: check-conflicts-dev check-conflicts-docker check-conflicts-prod

# ===========================================
# 🪄 HELP SYSTEM
# ===========================================
help: ## 🪄 Show this help message
	$(call print_banner)
	@echo -e "$(CYAN)Environment: $(ACTIVE_ENV) (using $(ACTIVE_ENV_FILE))$(NC)"
	
	$(call print_section,✨ Quick Start)
	@echo -e "  $(PURPLE)install$(NC)              🎯 Auto-detect and install environment"
	@echo -e "  $(PURPLE)install-dev$(NC)          🛠️  Local development environment"
	@echo -e "  $(PURPLE)dev$(NC)                  🔧 Start development mode"
	@echo -e "  $(PURPLE)docker$(NC)               🐳 Docker development stack"
	@echo -e "  $(PURPLE)prod$(NC)                 🚀 Production Docker stack"
	
	$(call print_section,🪄 Prerequisites)
	@echo -e "  $(PURPLE)install-prerequisites$(NC) 📦 System dependencies (all platforms)"
	@echo -e "  $(PURPLE)install-uv$(NC)           ⚡ UV Python package manager"
	@echo -e "  $(PURPLE)verify-prerequisites$(NC) ✅ Verify installation"
	@echo -e "  $(PURPLE)check-system$(NC)         🔍 Check system status"
	
	$(call print_section,🎛️ Service Management)
	@echo -e "  $(PURPLE)start$(NC)                ▶️  Start services (auto-detect)"
	@echo -e "  $(PURPLE)stop$(NC)                 ⏹️  Stop all services"
	@echo -e "  $(PURPLE)restart$(NC)              🔄 Restart services"
	@echo -e "  $(PURPLE)status$(NC)               📊 Show service status"
	@echo -e "  $(PURPLE)logs$(NC)                 📋 View colorized logs"
	@echo -e "  $(PURPLE)health$(NC)               💊 Health check"
	
	$(call print_section,🗄️ Database & Services)
	@echo -e "  $(PURPLE)install-postgres$(NC)     🐘 PostgreSQL database"
	@echo -e "  $(PURPLE)install-neo4j$(NC)        🔗 Neo4j graph database"
	@echo -e "  $(PURPLE)install-graphiti$(NC)     🧠 Knowledge graph service"
	@echo -e "  $(PURPLE)db-init$(NC)              🎯 Initialize database"
	@echo -e "  $(PURPLE)db-migrate$(NC)           📈 Run migrations"
	@echo -e "  $(PURPLE)db-reset$(NC)             🗑️  Reset database $(RED)(destructive!)$(NC)"
	
	$(call print_section,🛠️ Development)
	@echo -e "  $(PURPLE)test$(NC)                 🧪 Run test suite"
	@echo -e "  $(PURPLE)lint$(NC)                 🔍 Code linting"
	@echo -e "  $(PURPLE)format$(NC)               ✨ Format code"
	@echo -e "  $(PURPLE)requirements-update$(NC)  📦 Update dependencies"
	
	$(call print_section,🐳 Docker & Production)
	@echo -e "  $(PURPLE)install-docker$(NC)       🐳 Docker environment"
	@echo -e "  $(PURPLE)install-prod$(NC)         🚀 Production environment"
	@echo -e "  $(PURPLE)docker-build$(NC)         🔨 Build Docker images"
	@echo -e "  $(PURPLE)docker-clean$(NC)         🧹 Clean Docker resources"
	
	$(call print_section,🧹 Maintenance)
	@echo -e "  $(PURPLE)clean$(NC)                🧹 Clean temporary files"
	@echo -e "  $(PURPLE)reset$(NC)                💥 Full reset $(RED)(destructive!)$(NC)"
	@echo -e "  $(PURPLE)venv-clean$(NC)           🗑️  Remove virtual environment"
	
	@echo ""
	@echo -e "$(CYAN)$(SPARKLE) Pro tip: Use $(YELLOW)'make <target> FORCE=1'$(CYAN) to force operations$(NC)"
	@echo -e "$(CYAN)🔗 More info: $(YELLOW)https://github.com/namastexlabs/automagik-agents$(NC)"
	@echo ""

# ===========================================
# 🪄 SYSTEM CHECKS
# ===========================================
check-system: ## 🔍 Check system prerequisites
	$(call print_status,Checking system prerequisites...)
	@echo ""
	@echo -e "$(PURPLE)Python:$(NC)"
	@python3 --version 2>/dev/null || (echo -e "$(RED)$(ERROR) Python 3 not found$(NC)" && exit 1)
	@echo -e "$(GREEN)$(CHECKMARK) Python 3 found$(NC)"
	@echo ""
	@echo -e "$(PURPLE)Docker:$(NC)"
	@docker --version 2>/dev/null || echo -e "$(YELLOW)$(WARNING) Docker not found - required for Docker mode$(NC)"
	@docker-compose --version 2>/dev/null || echo -e "$(YELLOW)$(WARNING) Docker Compose not found - required for Docker mode$(NC)"
	@echo ""
	@echo -e "$(PURPLE)Environment:$(NC)"
	@if [ -f "$(ACTIVE_ENV_FILE)" ]; then \
		echo -e "$(GREEN)$(CHECKMARK) Environment file $(ACTIVE_ENV_FILE) found$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) Environment file $(ACTIVE_ENV_FILE) not found$(NC)"; \
	fi
	@echo ""
	@echo -e "$(PURPLE)Virtual Environment:$(NC)"
	@if [ -d "$(VENV_PATH)" ]; then \
		echo -e "$(GREEN)$(CHECKMARK) Virtual environment found at $(VENV_PATH)$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) Virtual environment not found - run 'make install-dev'$(NC)"; \
	fi

# ===========================================
# 🪄 PREREQUISITE INSTALLATION SYSTEM
# ===========================================

# OS detection variables
UNAME_S := $(shell uname -s)
DISTRO := $(shell lsb_release -si 2>/dev/null || echo "Unknown")

install-prerequisites: ## 🔧 Install system prerequisites for all platforms
	$(call print_status,Installing system prerequisites...)
	@echo -e "$(CYAN)Detected OS: $(UNAME_S)$(NC)"
	@if [ "$(DISTRO)" != "Unknown" ]; then \
		echo -e "$(CYAN)Distribution: $(DISTRO)$(NC)"; \
	fi
	@echo ""
	@if [ "$(UNAME_S)" = "Linux" ]; then \
		$(MAKE) install-prerequisites-linux; \
	elif [ "$(UNAME_S)" = "Darwin" ]; then \
		$(MAKE) install-prerequisites-mac; \
	else \
		$(call print_error,Unsupported operating system: $(UNAME_S)); \
		exit 1; \
	fi
	@$(MAKE) install-uv
	@$(MAKE) verify-prerequisites
	@echo ""
	$(call magic_loading,Casting installation spells)
	$(call print_success,System prerequisites installation complete!)
	@echo -e "$(CYAN)$(SPARKLE) Run 'make install-dev' to set up the Python environment$(NC)"

install-prerequisites-linux: ## 🐧 Install Linux system prerequisites
	$(call print_status,Installing Linux prerequisites...)
	@if command -v apt-get >/dev/null 2>&1; then \
		$(MAKE) install-prerequisites-debian; \
	elif command -v yum >/dev/null 2>&1; then \
		$(MAKE) install-prerequisites-rhel; \
	elif command -v dnf >/dev/null 2>&1; then \
		$(MAKE) install-prerequisites-fedora; \
	elif command -v pacman >/dev/null 2>&1; then \
		$(MAKE) install-prerequisites-arch; \
	else \
		$(call print_error,Unsupported Linux distribution); \
		echo -e "$(YELLOW)💡 Please install manually: python3.12, docker, docker-compose, nodejs, make, curl, jq, ccze, git$(NC)"; \
		exit 1; \
	fi

install-prerequisites-debian: ## 📦 Install Debian/Ubuntu prerequisites
	$(call print_status,Installing Debian/Ubuntu packages...)
	@echo -e "$(CYAN)Updating package lists...$(NC)"
	@sudo apt-get update -qq
	@echo -e "$(CYAN)Installing core packages...$(NC)"
	@sudo apt-get install -y -qq \
		make curl jq git build-essential \
		software-properties-common apt-transport-https ca-certificates gnupg lsb-release >/dev/null 2>&1 && \
	echo -e "$(GREEN)$(CHECKMARK) Core packages ready$(NC)" || \
	sudo apt-get install -y \
		make curl jq git build-essential \
		software-properties-common apt-transport-https ca-certificates gnupg lsb-release
	@echo -e "$(CYAN)Installing Python 3.12...$(NC)"
	@if ! apt-cache show python3.12 >/dev/null 2>&1; then \
		echo -e "$(CYAN)Adding deadsnakes PPA for Python 3.12...$(NC)"; \
		sudo add-apt-repository ppa:deadsnakes/ppa -y; \
		sudo apt-get update -qq; \
	fi
	@if apt-cache show python3.12 >/dev/null 2>&1; then \
		sudo apt-get install -y -qq python3.12 python3.12-pip python3.12-venv python3.12-dev >/dev/null 2>&1 || \
		sudo apt-get install -y -qq python3.12 python3.12-venv python3.12-dev python3-pip >/dev/null 2>&1; \
		echo -e "$(GREEN)$(CHECKMARK) Python 3.12 installed$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) Installing available Python 3 version...$(NC)"; \
		sudo apt-get install -y -qq python3 python3-pip python3-venv python3-dev >/dev/null 2>&1; \
		echo -e "$(YELLOW)$(WARNING) Using system Python 3 (Python 3.12 recommended)$(NC)"; \
	fi
	@echo -e "$(CYAN)Installing Node.js 22 LTS...$(NC)"
	@if ! command -v node >/dev/null 2>&1 || ! node --version | grep -q "v22"; then \
		curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null 2>&1; \
		sudo apt-get install -y -qq nodejs >/dev/null 2>&1; \
		echo -e "$(GREEN)$(CHECKMARK) Node.js 22 LTS installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Node.js 22 already installed$(NC)"; \
	fi
	@echo -e "$(CYAN)Installing colorization tools...$(NC)"
	@sudo apt-get install -y -qq ccze multitail >/dev/null 2>&1 && \
	echo -e "$(GREEN)$(CHECKMARK) Colorization tools ready$(NC)" || \
	echo -e "$(YELLOW)$(WARNING) ccze/multitail not available in repos$(NC)"
	@echo -e "$(CYAN)Installing optional development tools...$(NC)"
	@sudo apt-get install -y -qq htop ncdu tree >/dev/null 2>&1 && \
	echo -e "$(GREEN)$(CHECKMARK) Development tools ready$(NC)" || \
	echo -e "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo -e "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo apt-get install -y -qq postgresql-client >/dev/null 2>&1 && \
	echo -e "$(GREEN)$(CHECKMARK) PostgreSQL client ready$(NC)" || \
	echo -e "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-debian

install-prerequisites-rhel: ## 📦 Install RHEL/CentOS prerequisites
	$(call print_status,Installing RHEL/CentOS packages...)
	@echo -e "$(CYAN)Installing core packages...$(NC)"
	@sudo yum install -y epel-release || echo -e "$(YELLOW)$(WARNING) EPEL repository not available$(NC)"
	@sudo yum install -y \
		python3.12 python3.12-pip python3.12-devel \
		make curl jq git gcc gcc-c++ \
		ca-certificates
	@echo -e "$(CYAN)Installing Node.js 22 LTS...$(NC)"
	@if ! command -v node >/dev/null 2>&1 || ! node --version | grep -q "v22"; then \
		curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -; \
		sudo yum install -y nodejs; \
		echo -e "$(GREEN)$(CHECKMARK) Node.js 22 LTS installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Node.js 22 already installed$(NC)"; \
	fi
	@echo -e "$(CYAN)Installing colorization tools...$(NC)"
	@sudo yum install -y ccze multitail || echo -e "$(YELLOW)$(WARNING) ccze/multitail not available in repos$(NC)"
	@echo -e "$(CYAN)Installing optional development tools...$(NC)"
	@sudo yum install -y htop ncdu tree || echo -e "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo -e "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo yum install -y postgresql || echo -e "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-rhel

install-prerequisites-fedora: ## 📦 Install Fedora prerequisites
	$(call print_status,Installing Fedora packages...)
	@echo -e "$(CYAN)Installing core packages...$(NC)"
	@sudo dnf install -y \
		python3.12 python3.12-pip python3.12-devel \
		make curl jq git gcc gcc-c++ \
		ca-certificates
	@echo -e "$(CYAN)Installing Node.js 22 LTS...$(NC)"
	@if ! command -v node >/dev/null 2>&1 || ! node --version | grep -q "v22"; then \
		curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -; \
		sudo dnf install -y nodejs; \
		echo -e "$(GREEN)$(CHECKMARK) Node.js 22 LTS installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Node.js 22 already installed$(NC)"; \
	fi
	@echo -e "$(CYAN)Installing colorization tools...$(NC)"
	@sudo dnf install -y ccze multitail || echo -e "$(YELLOW)$(WARNING) ccze/multitail not available in repos$(NC)"
	@echo -e "$(CYAN)Installing optional development tools...$(NC)"
	@sudo dnf install -y htop ncdu tree || echo -e "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo -e "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo dnf install -y postgresql || echo -e "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-fedora

install-prerequisites-arch: ## 📦 Install Arch Linux prerequisites
	$(call print_status,Installing Arch Linux packages...)
	@echo -e "$(CYAN)Updating package database...$(NC)"
	@sudo pacman -Sy
	@echo -e "$(CYAN)Installing core packages...$(NC)"
	@sudo pacman -S --noconfirm --needed \
		python python-pip \
		make curl jq git base-devel \
		ca-certificates nodejs npm
	@echo -e "$(CYAN)Installing colorization tools...$(NC)"
	@sudo pacman -S --noconfirm --needed ccze multitail || echo -e "$(YELLOW)$(WARNING) ccze/multitail not available$(NC)"
	@echo -e "$(CYAN)Installing optional development tools...$(NC)"
	@sudo pacman -S --noconfirm --needed htop ncdu tree || echo -e "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo -e "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo pacman -S --noconfirm --needed postgresql-libs || echo -e "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-arch

install-prerequisites-mac: ## 🍎 Install macOS prerequisites
	$(call print_status,Installing macOS prerequisites...)
	@if ! command -v brew >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Homebrew...$(NC)"; \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
		echo -e "$(GREEN)$(CHECKMARK) Homebrew installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Homebrew already installed$(NC)"; \
	fi
	@echo -e "$(CYAN)Updating Homebrew...$(NC)"
	@brew update
	@echo -e "$(CYAN)Installing core packages...$(NC)"
	@brew install python@3.12 || brew install python@3.11 || brew install python3
	@brew install make curl jq git
	@echo -e "$(CYAN)Installing Node.js 22 LTS...$(NC)"
	@brew install node@22 || brew install node
	@echo -e "$(CYAN)Installing colorization tools...$(NC)"
	@brew install ccze multitail || echo -e "$(YELLOW)$(WARNING) ccze/multitail not available$(NC)"
	@echo -e "$(CYAN)Installing optional development tools...$(NC)"
	@brew install htop ncdu tree || echo -e "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo -e "$(CYAN)Installing PostgreSQL client...$(NC)"
	@brew install postgresql || echo -e "$(YELLOW)$(WARNING) PostgreSQL not available$(NC)"
	@echo -e "$(CYAN)Installing Docker...$(NC)"
	@brew install --cask docker || echo -e "$(YELLOW)$(WARNING) Docker installation may require manual setup$(NC)"

# Docker installation for different Linux distributions
install-docker-debian: ## 🐳 Install Docker on Debian/Ubuntu
	@if ! command -v docker >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker for Debian/Ubuntu...$(NC)"; \
		curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg; \
		echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null; \
		sudo apt-get update -qq; \
		sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io >/dev/null 2>&1; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo -e "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo -e "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker Compose...$(NC)"; \
		sudo apt-get install -y -qq docker-compose-plugin >/dev/null 2>&1; \
		echo -e "$(GREEN)$(CHECKMARK) Docker Compose installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker Compose already installed$(NC)"; \
	fi

install-docker-rhel: ## 🐳 Install Docker on RHEL/CentOS
	@if ! command -v docker >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker for RHEL/CentOS...$(NC)"; \
		sudo yum install -y yum-utils; \
		sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo; \
		sudo yum install -y docker-ce docker-ce-cli containerd.io; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo -e "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo -e "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker Compose...$(NC)"; \
		sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$$(uname -s)-$$(uname -m)" -o /usr/local/bin/docker-compose; \
		sudo chmod +x /usr/local/bin/docker-compose; \
		echo -e "$(GREEN)$(CHECKMARK) Docker Compose installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker Compose already installed$(NC)"; \
	fi

install-docker-fedora: ## 🐳 Install Docker on Fedora
	@if ! command -v docker >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker for Fedora...$(NC)"; \
		sudo dnf -y install dnf-plugins-core; \
		sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo; \
		sudo dnf install -y docker-ce docker-ce-cli containerd.io; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo -e "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo -e "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker Compose...$(NC)"; \
		sudo dnf install -y docker-compose-plugin; \
		echo -e "$(GREEN)$(CHECKMARK) Docker Compose installed$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker Compose already installed$(NC)"; \
	fi

install-docker-arch: ## 🐳 Install Docker on Arch Linux
	@if ! command -v docker >/dev/null 2>&1; then \
		echo -e "$(CYAN)Installing Docker for Arch Linux...$(NC)"; \
		sudo pacman -S --noconfirm --needed docker docker-compose; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo -e "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo -e "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi

install-uv: ## ⚡ Install uv Python package manager
	@if ! command -v uv >/dev/null 2>&1; then \
		$(call print_status,Installing uv Python package manager...); \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo -e "$(GREEN)$(CHECKMARK) uv installed$(NC)"; \
		echo -e "$(YELLOW)💡 You may need to restart your shell or run: source ~/.bashrc$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) uv already installed$(NC)"; \
	fi

verify-prerequisites: ## ✅ Verify all prerequisites are properly installed
	$(call print_status,Verifying prerequisites installation...)
	@echo ""
	@echo -e "$(PURPLE)🐍 Python:$(NC)"
	@if command -v python3.12 >/dev/null 2>&1; then \
		version=$$(python3.12 --version 2>&1); \
		echo -e "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	elif command -v python3 >/dev/null 2>&1; then \
		version=$$(python3 --version 2>&1); \
		echo -e "$(YELLOW)$(WARNING) $$version (preferably use Python 3.12)$(NC)"; \
	else \
		echo -e "$(RED)$(ERROR) Python 3 not found$(NC)"; \
	fi
	@echo ""
	@echo -e "$(PURPLE)🟩 Node.js:$(NC)"
	@if command -v node >/dev/null 2>&1; then \
		version=$$(node --version 2>&1); \
		if echo "$$version" | grep -q "v22"; then \
			echo -e "$(GREEN)$(CHECKMARK) Node.js $$version (LTS)$(NC)"; \
		else \
			echo -e "$(YELLOW)$(WARNING) Node.js $$version (v22 LTS recommended)$(NC)"; \
		fi; \
	else \
		echo -e "$(RED)$(ERROR) Node.js not found$(NC)"; \
	fi
	@if command -v npx >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) npx available$(NC)"; \
	else \
		echo -e "$(RED)$(ERROR) npx not found$(NC)"; \
	fi
	@echo ""
	@echo -e "$(PURPLE)🐳 Docker:$(NC)"
	@if docker --version >/dev/null 2>&1; then \
		version=$$(docker --version); \
		echo -e "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) Docker not found$(NC)"; \
	fi
	@if docker-compose --version >/dev/null 2>&1; then \
		version=$$(docker-compose --version); \
		echo -e "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) Docker Compose not found$(NC)"; \
	fi
	@echo ""
	@echo -e "$(PURPLE)🔧 Build Tools:$(NC)"
	@if make --version >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) make installed$(NC)"; \
	else \
		echo -e "$(RED)$(ERROR) make not found$(NC)"; \
	fi
	@if curl --version >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) curl installed$(NC)"; \
	else \
		echo -e "$(RED)$(ERROR) curl not found$(NC)"; \
	fi
	@if jq --version >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) jq installed$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) jq not found$(NC)"; \
	fi
	@if git --version >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) git installed$(NC)"; \
	else \
		echo -e "$(RED)$(ERROR) git not found$(NC)"; \
	fi
	@echo ""
	@echo -e "$(PURPLE)🎨 Optional Tools:$(NC)"
	@if ccze --version >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) ccze installed (colorized logs)$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) ccze not found (plain logs)$(NC)"; \
	fi
	@if multitail -V >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) multitail installed$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) multitail not found$(NC)"; \
	fi
	@if htop --version >/dev/null 2>&1; then \
		echo -e "$(GREEN)$(CHECKMARK) htop installed$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) htop not found$(NC)"; \
	fi
	@echo ""
	@echo -e "$(PURPLE)⚡ Package Manager:$(NC)"
	@if uv --version >/dev/null 2>&1; then \
		version=$$(uv --version); \
		echo -e "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) uv not found$(NC)"; \
	fi

# ===========================================
# 🪄 STATUS DETECTION
# ===========================================
detect-mode: ## 🔍 Detect current running mode
	@echo "$(shell $(call detect_mode))"

# Internal target for checking if we should proceed with potentially destructive operations
check-force:
	@if [ -z "$(FORCE)" ]; then \
		$(call print_warning,This operation may conflict with running services); \
		echo -e "$(YELLOW)💡 Use 'make $@ FORCE=1' to proceed anyway$(NC)"; \
		exit 1; \
	fi

# ===========================================
# 🪄 PM2-STYLE STATUS DISPLAY
# ===========================================
status: ## 📊 Show PM2-style status table
	$(call print_status,Automagik Agents Status)
	@echo ""
	@echo -e "$(BOLD_PURPLE)┌────┬─────────────────────────┬──────────┬───────┬────────┬──────────┬──────────┐$(NC)"
	@echo -e "$(BOLD_PURPLE)│ id │ name                    │ mode     │ port  │ pid    │ uptime   │ status   │$(NC)"
	@echo -e "$(BOLD_PURPLE)├────┼─────────────────────────┼──────────┼───────┼────────┼──────────┼──────────┤$(NC)"
	@$(call show_docker_instances)
	@$(call show_local_instances)
	@$(call show_service_instances)
	@echo -e "$(BOLD_PURPLE)└────┴─────────────────────────┴──────────┴───────┴────────┴──────────┴──────────┘$(NC)"
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
	echo -e "$(PURPLE)🪄 Mode: $$mode | Docker: $$docker_count | Local: $$local_count | Service: $$service_active$(NC)"

define show_docker_instances
	@id=0; \
	docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | grep "automagik" | while IFS=$$'\t' read -r name status ports; do \
		uptime_raw=$$(echo "$$status" | sed 's/Up //g' | sed 's/ (.*//g'); \
		if echo "$$uptime_raw" | grep -q "hour"; then \
			if echo "$$uptime_raw" | grep -q "About an hour"; then \
				uptime="1h"; \
			else \
				hours=$$(echo "$$uptime_raw" | sed 's/About \([0-9]*\) hours*.*/\1/' | sed 's/[^0-9]*\([0-9]*\).*/\1/'); \
				uptime="$${hours}h"; \
			fi; \
		elif echo "$$uptime_raw" | grep -q "minute"; then \
			if echo "$$uptime_raw" | grep -q "About a minute"; then \
				uptime="1m"; \
			else \
				mins=$$(echo "$$uptime_raw" | sed 's/About \([0-9]*\) minutes*.*/\1/' | sed 's/[^0-9]*\([0-9]*\).*/\1/'); \
				uptime="$${mins}m"; \
			fi; \
		elif echo "$$uptime_raw" | grep -q "second"; then \
			secs=$$(echo "$$uptime_raw" | sed 's/About \([0-9]*\) seconds*.*/\1/' | sed 's/[^0-9]*\([0-9]*\).*/\1/'); \
			uptime="$${secs}s"; \
		else \
			uptime=$$(echo "$$uptime_raw" | head -c 8); \
		fi; \
		port=$$(echo "$$ports" | grep -o '[0-9]*->[0-9]*' | head -1 | cut -d'>' -f2 | cut -d'/' -f1); \
		if [ -z "$$port" ]; then \
			port=$$(echo "$$ports" | grep -o '[0-9]*:[0-9]*->[0-9]*' | head -1 | cut -d'>' -f2 | cut -d'/' -f1); \
		fi; \
		if [ -z "$$port" ]; then port="-"; fi; \
		container_id=$$(docker ps --format "{{.ID}}" --filter "name=$$name" | head -c 6); \
		name_short=$$(echo $$name | head -c 23); \
		printf "$(BOLD_PURPLE)│$(NC) %-2s $(BOLD_PURPLE)│$(NC) %-23s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) $(GREEN)%-8s$(NC) $(BOLD_PURPLE)│$(NC)\n" \
			"$$id" "$$name_short" "docker" "$$port" "$$container_id" "$$uptime" "online"; \
		id=$$((id + 1)); \
	done
endef

define show_local_instances
	@if pgrep -f "uvicorn.*automagik" >/dev/null 2>&1; then \
		pid=$$(pgrep -f "uvicorn.*automagik"); \
		port=$$(netstat -tlnp 2>/dev/null | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
		uptime_raw=$$(ps -o etime= -p $$pid | tr -d ' '); \
		if echo "$$uptime_raw" | grep -q ":"; then \
			uptime=$$(echo "$$uptime_raw" | head -c 8); \
		else \
			uptime="$$uptime_raw"; \
		fi; \
		id=$$(docker ps --filter "name=automagik" --format "{{.Names}}" 2>/dev/null | wc -l); \
		\
		if [ -z "$$port" ]; then \
			port="-"; \
			status="error"; \
			status_color="$(RED)"; \
		else \
			if curl -s "http://localhost:$$port/health" >/dev/null 2>&1; then \
				status="online"; \
				status_color="$(GREEN)"; \
			else \
				status="unhealthy"; \
				status_color="$(YELLOW)"; \
			fi; \
		fi; \
		\
		printf "$(BOLD_PURPLE)│$(NC) %-2s $(BOLD_PURPLE)│$(NC) %-23s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) $${status_color}%-8s$(NC) $(BOLD_PURPLE)│$(NC)\n" \
			"$$id" "automagik-local" "process" "$$port" "$$pid" "$$uptime" "$$status"; \
	fi
endef

define show_service_instances
	@if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		pid=$$(systemctl show automagik-agents --property=MainPID --value 2>/dev/null); \
		if [ "$$pid" != "0" ] && [ -n "$$pid" ]; then \
			port=$$(netstat -tlnp 2>/dev/null | grep $$pid | awk '{print $$4}' | cut -d: -f2 | head -1); \
			if [ -z "$$port" ]; then port="-"; fi; \
			uptime_sec=$$(systemctl show automagik-agents --property=ActiveEnterTimestamp --value 2>/dev/null | xargs -I {} date -d "{}" +%s 2>/dev/null | xargs -I {} echo "scale=0; ($$(date +%s) - {}) / 60" | bc 2>/dev/null || echo "0"); \
			if [ "$$uptime_sec" -gt 1440 ]; then \
				days=$$(echo "scale=0; $$uptime_sec / 1440" | bc); \
				uptime="$${days}d"; \
			elif [ "$$uptime_sec" -gt 60 ]; then \
				hours=$$(echo "scale=0; $$uptime_sec / 60" | bc); \
				uptime="$${hours}h"; \
			else \
				uptime="$${uptime_sec}m"; \
			fi; \
			id=$$(docker ps --filter "name=automagik" --format "{{.Names}}" 2>/dev/null | wc -l); \
			if pgrep -f "uvicorn.*automagik" >/dev/null 2>&1; then id=$$((id + 1)); fi; \
			printf "$(BOLD_PURPLE)│$(NC) %-2s $(BOLD_PURPLE)│$(NC) %-23s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) $(GREEN)%-8s$(NC) $(BOLD_PURPLE)│$(NC)\n" \
				"$$id" "automagik-svc" "service" "$$port" "$$pid" "$$uptime" "online"; \
		else \
			id=$$(docker ps --filter "name=automagik" --format "{{.Names}}" 2>/dev/null | wc -l); \
			if pgrep -f "uvicorn.*automagik" >/dev/null 2>&1; then id=$$((id + 1)); fi; \
			printf "$(BOLD_PURPLE)│$(NC) %-2s $(BOLD_PURPLE)│$(NC) %-23s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) $(RED)%-8s$(NC) $(BOLD_PURPLE)│$(NC)\n" \
				"$$id" "automagik-svc" "service" "-" "-" "-" "error"; \
		fi; \
	else \
		id=$$(docker ps --filter "name=automagik" --format "{{.Names}}" 2>/dev/null | wc -l); \
		if pgrep -f "uvicorn.*automagik" >/dev/null 2>&1; then id=$$((id + 1)); fi; \
		printf "$(BOLD_PURPLE)│$(NC) %-2s $(BOLD_PURPLE)│$(NC) %-23s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) %-5s $(BOLD_PURPLE)│$(NC) %-6s $(BOLD_PURPLE)│$(NC) %-8s $(BOLD_PURPLE)│$(NC) $(YELLOW)%-8s$(NC) $(BOLD_PURPLE)│$(NC)\n" \
			"$$id" "automagik-svc" "service" "-" "-" "-" "stopped"; \
	fi
endef

# ===========================================
# 🪄 COLORFUL LOG VIEWING SYSTEM
# ===========================================
logs: ## 📄 View colorized logs (auto-detect source)
	@$(call print_status,Automagik Agents Logs)
	@$(call detect_and_show_logs,50)

logs-f: ## 📄 Follow logs in real-time
	@$(call print_status,Following Automagik Agents Logs - Press Ctrl+C to stop)
	@$(call detect_and_follow_logs)

logs-100: ## 📄 View last 100 log lines
	@$(call print_status,Automagik Agents Logs - Last 100 lines)
	@$(call detect_and_show_logs,100)

logs-500: ## 📄 View last 500 log lines
	@$(call print_status,Automagik Agents Logs - Last 500 lines)
	@$(call detect_and_show_logs,500)

# Log source detection and display
define detect_and_show_logs
	@echo -e "$(CYAN)🔍 Detecting log sources...$(NC)"; \
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo -e "$(GREEN)📋 Found systemd service logs$(NC)"; \
		$(call show_service_logs,$(1)); \
	elif docker ps --filter "name=automagik" --format "{{.Names}}" | head -1 | grep -q automagik; then \
		primary_container=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | grep -E "(automagik_agents|automagik-agents)" | head -1); \
		echo -e "$(GREEN)🐳 Found Docker logs for: $$primary_container$(NC)"; \
		$(call show_docker_logs,$$primary_container,$(1)); \
	elif [ -f "logs/automagik.log" ]; then \
		echo -e "$(GREEN)📁 Found local log file$(NC)"; \
		$(call show_file_logs,$(1)); \
	else \
		echo -e "$(YELLOW)$(WARNING) No log sources found$(NC)"; \
		echo -e "$(CYAN)💡 Available sources: systemd service, docker containers, log files$(NC)"; \
	fi
endef

define detect_and_follow_logs
	@if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo -e "$(GREEN)📋 Following systemd service logs$(NC)"; \
		$(call follow_service_logs); \
	elif docker ps --filter "name=automagik" --format "{{.Names}}" | head -1 | grep -q automagik; then \
		primary_container=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | grep -E "(automagik_agents|automagik-agents)" | head -1); \
		echo -e "$(GREEN)🐳 Following Docker logs for: $$primary_container$(NC)"; \
		$(call follow_docker_logs,$$primary_container); \
	elif [ -f "logs/automagik.log" ]; then \
		echo -e "$(GREEN)📁 Following local log file$(NC)"; \
		$(call follow_file_logs); \
	else \
		echo -e "$(YELLOW)$(WARNING) No log sources found to follow$(NC)"; \
	fi
endef

# Service logs
define show_service_logs
	journalctl -u automagik-agents -n $(1) --no-pager 2>/dev/null | $(call colorize_logs) || \
	echo -e "$(RED)$(ERROR) Unable to access systemd logs$(NC)"
endef

define follow_service_logs
	journalctl -u automagik-agents -f --no-pager 2>/dev/null | $(call colorize_logs) || \
	echo -e "$(RED)$(ERROR) Unable to follow systemd logs$(NC)"
endef

# Docker logs
define show_docker_logs
	docker logs --tail $(2) $(1) 2>&1 | $(call colorize_logs) || \
	echo -e "$(RED)$(ERROR) Unable to access Docker logs for $(1)$(NC)"
endef

define follow_docker_logs
	docker logs -f $(1) 2>&1 | $(call colorize_logs) || \
	echo -e "$(RED)$(ERROR) Unable to follow Docker logs for $(1)$(NC)"
endef

# File logs
define show_file_logs
	tail -n $(1) logs/automagik.log 2>/dev/null | $(call colorize_logs) || \
	echo -e "$(RED)$(ERROR) Unable to access log file$(NC)"
endef

define follow_file_logs
	tail -f logs/automagik.log 2>/dev/null | $(call colorize_logs) || \
	echo -e "$(RED)$(ERROR) Unable to follow log file$(NC)"
endef

# Log colorization with graceful fallback
define colorize_logs
	if command -v ccze >/dev/null 2>&1; then \
		ccze -A; \
	else \
		echo -e "$(YELLOW)$(WARNING) ccze not available - showing plain logs$(NC)" >&2; \
		cat; \
	fi
endef

# Specific container log viewing
logs-docker: ## 🐳 View Docker container logs (interactive selection)
	@$(call print_status,Docker Container Logs)
	@containers=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | sort); \
	if [ -z "$$containers" ]; then \
		echo -e "$(RED)$(ERROR) No automagik Docker containers running$(NC)"; \
		exit 1; \
	fi; \
	echo -e "$(CYAN)Available containers:$(NC)"; \
	i=1; \
	for container in $$containers; do \
		echo "  $$i) $$container"; \
		i=$$((i+1)); \
	done; \
	echo ""; \
	read -p "Select container (1-$$((i-1))): " choice; \
	selected=$$(echo "$$containers" | sed -n "$${choice}p"); \
	if [ -n "$$selected" ]; then \
		echo -e "$(GREEN)📋 Showing logs for: $$selected$(NC)"; \
		docker logs --tail 100 $$selected 2>&1 | $(call colorize_logs); \
	else \
		echo -e "$(RED)$(ERROR) Invalid selection$(NC)"; \
	fi

logs-all: ## 📄 View logs from all sources
	@$(call print_status,All Automagik Logs)
	@echo -e "$(PURPLE)🔍 Checking all log sources...$(NC)"
	@echo ""
	@if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo "$(BOLD_PURPLE)📋 Systemd Service Logs:$(NC)"; \
		$(call show_service_logs,20); \
		echo ""; \
	fi
	@containers=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | grep -E "(automagik_agents|automagik-agents)" | head -3); \
	for container in $$containers; do \
		echo "$(BOLD_PURPLE)🐳 Docker Logs [$$container]:$(NC)"; \
		$(call show_docker_logs,$$container,10); \
		echo ""; \
	done
	@if [ -f "logs/automagik.log" ]; then \
		echo "$(BOLD_PURPLE)📁 Local File Logs:$(NC)"; \
		$(call show_file_logs,10); \
	fi

# ===========================================
# 🪄 INSTALLATION TARGETS
# ===========================================

install: ## 🚀 Auto-detect and install appropriate environment
	@$(call print_status,Auto-detecting installation mode...)
	@if [ -f "$(PROD_ENV_FILE)" ]; then \
		echo -e "$(CYAN)Production environment detected - installing prod mode$(NC)"; \
		$(MAKE) install-prod; \
	elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
		echo -e "$(CYAN)Docker available - installing docker mode$(NC)"; \
		$(MAKE) install-docker; \
	else \
		echo -e "$(CYAN)Standard environment - installing dev mode$(NC)"; \
		$(MAKE) install-dev; \
	fi

install-dev: ## 🛠️ Install development environment
	$(call print_banner)
	$(call print_status,Installing development environment...)
	@echo ""
	@$(MAKE) install-prerequisites
	@$(MAKE) install-python-env
	@$(MAKE) check-env-dev
	@$(MAKE) install-database-local
	@echo ""
	$(call print_success,Development environment installed!)
	@echo -e "$(CYAN)$(SPARKLE) Next steps:$(NC)"
	@echo -e "  $(PURPLE)make dev$(NC)     Start development server"
	@echo -e "  $(PURPLE)make test$(NC)    Run test suite"
	@echo -e "  $(PURPLE)make status$(NC)  Check service status"

install-docker: ## 🐳 Install Docker development environment
	$(call print_banner)
	$(call print_status,Installing Docker development environment...)
	@echo ""
	@$(MAKE) verify-docker
	@$(MAKE) install-prerequisites
	@$(MAKE) check-env-dev
	@$(MAKE) docker-build
	@echo ""
	$(call print_success,Docker development environment installed!)
	@echo -e "$(CYAN)$(SPARKLE) Next steps:$(NC)"
	@echo -e "  $(PURPLE)make docker$(NC)  Start Docker stack"
	@echo -e "  $(PURPLE)make logs$(NC)    View container logs"
	@echo -e "  $(PURPLE)make status$(NC)  Check container status"

install-prod: ## 🏭 Install production environment
	$(call print_banner)
	$(call print_status,Installing production environment...)
	@echo ""
	@$(MAKE) verify-docker
	@$(MAKE) install-prerequisites
	@$(MAKE) check-env-prod
	@$(MAKE) docker-build
	@$(MAKE) setup-prod-volumes
	@echo ""
	$(call print_success,Production environment installed!)
	@echo -e "$(CYAN)$(SPARKLE) Next steps:$(NC)"
	@echo -e "  $(PURPLE)make prod$(NC)    Start production stack"
	@echo -e "  $(PURPLE)make health$(NC)  Check service health"
	@echo -e "  $(PURPLE)make logs$(NC)    View production logs"

install-service: ## ⚙️ Install systemd service (requires install-dev first)
	$(call print_status,Installing systemd service...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo -e "$(YELLOW)$(WARNING) Development environment not found$(NC)"; \
		echo -e "$(CYAN)💡 Running install-dev first...$(NC)"; \
		$(MAKE) install-dev; \
	fi
	@$(call create_systemd_service)
	@sudo systemctl daemon-reload
	@sudo systemctl enable automagik-agents
	$(call print_success,Systemd service installed!)
	@echo -e "$(CYAN)💡 Service commands:$(NC)"
	@echo "  $(PURPLE)sudo systemctl start automagik-agents$(NC)   Start service"
	@echo "  $(PURPLE)sudo systemctl status automagik-agents$(NC)  Check status"
	@echo "  $(PURPLE)make logs$(NC)                               View logs"

# ===========================================
# 🪄 PYTHON ENVIRONMENT MANAGEMENT
# ===========================================

install-python-env: ## 🐍 Install Python virtual environment
	$(call print_status,Setting up Python environment...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo -e "$(CYAN)Creating virtual environment with Python 3.12...$(NC)"; \
		if command -v python3.12 >/dev/null 2>&1; then \
			python3.12 -m venv $(VENV_PATH); \
		elif command -v python3 >/dev/null 2>&1; then \
			python3 -m venv $(VENV_PATH); \
		else \
			echo -e "$(RED)$(ERROR) Python 3 not found$(NC)"; \
			exit 1; \
		fi; \
		echo -e "$(GREEN)$(CHECKMARK) Virtual environment created$(NC)"; \
	else \
		echo -e "$(GREEN)$(CHECKMARK) Virtual environment already exists$(NC)"; \
	fi
	@echo -e "$(CYAN)Installing dependencies with uv...$(NC)"
	@$(VENV_PATH)/bin/python -m pip install --upgrade pip
	@if command -v uv >/dev/null 2>&1; then \
		. $(VENV_PATH)/bin/activate && uv sync; \
		echo -e "$(GREEN)$(CHECKMARK) Dependencies installed with uv$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) uv not found, using pip...$(NC)"; \
		$(VENV_PATH)/bin/pip install -e .; \
		echo -e "$(GREEN)$(CHECKMARK) Dependencies installed with pip$(NC)"; \
	fi

venv-create: install-python-env ## 🐍 Create virtual environment (alias)

venv-clean: ## 🧹 Remove virtual environment
	$(call print_status,Removing virtual environment...)
	@if [ -d "$(VENV_PATH)" ]; then \
		rm -rf "$(VENV_PATH)"; \
		echo -e "$(GREEN)$(CHECKMARK) Virtual environment removed$(NC)"; \
	else \
		echo -e "$(YELLOW)$(WARNING) Virtual environment not found$(NC)"; \
	fi

requirements-update: ## 📦 Update Python dependencies
	$(call check_venv)
	$(call print_status,Updating Python dependencies...)
	@if command -v uv >/dev/null 2>&1; then \
		. $(VENV_PATH)/bin/activate && uv sync --upgrade; \
	else \
		$(PIP) install --upgrade -e .; \
	fi
	$(call print_success,Dependencies updated!)

# ===========================================
# 🪄 INDIVIDUAL SERVICE INSTALLATION
# ===========================================

install-postgres: ## 🐘 Install PostgreSQL service
	$(call print_status,Installing PostgreSQL...)
	@$(call verify_docker)
	@docker-compose -f $(DOCKER_COMPOSE_FILE) up -d automagik-agents-db
	@echo -e "$(CYAN)Waiting for PostgreSQL to be ready...$(NC)"
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f $(DOCKER_COMPOSE_FILE) exec -T automagik-agents-db pg_isready -U postgres >/dev/null 2>&1; then \
			echo -e "$(GREEN)$(CHECKMARK) PostgreSQL is ready$(NC)"; \
			break; \
		fi; \
		echo -e "$(YELLOW)Waiting for PostgreSQL... ($$timeout seconds remaining)$(NC)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo -e "$(RED)$(ERROR) PostgreSQL failed to start$(NC)"; \
		exit 1; \
	fi

install-neo4j: ## 🔗 Install Neo4j service (for graphiti profile)
	$(call print_status,Installing Neo4j...)
	@$(call verify_docker)
	@docker-compose -f $(DOCKER_COMPOSE_FILE) --profile graphiti up -d automagik-agents-neo4j
	@echo -e "$(CYAN)Waiting for Neo4j to be ready...$(NC)"
	@timeout=90; \
	while [ $$timeout -gt 0 ]; do \
		if curl -s http://localhost:7474 >/dev/null 2>&1; then \
			echo -e "$(GREEN)$(CHECKMARK) Neo4j is ready$(NC)"; \
			break; \
		fi; \
		echo -e "$(YELLOW)Waiting for Neo4j... ($$timeout seconds remaining)$(NC)"; \
		sleep 3; \
		timeout=$$((timeout - 3)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo -e "$(RED)$(ERROR) Neo4j failed to start$(NC)"; \
		exit 1; \
	fi

install-graphiti: ## 🕸️ Install Graphiti service (requires Neo4j)
	$(call print_status,Installing Graphiti...)
	@$(call verify_docker)
	@if ! docker ps | grep -q automagik-agents-neo4j; then \
		echo -e "$(CYAN)Neo4j not running, starting it first...$(NC)"; \
		$(MAKE) install-neo4j; \
	fi
	@docker-compose -f $(DOCKER_COMPOSE_FILE) --profile graphiti up -d automagik-agents-graphiti
	@echo -e "$(CYAN)Waiting for Graphiti to be ready...$(NC)"
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if curl -s http://localhost:8000/healthcheck >/dev/null 2>&1; then \
			echo -e "$(GREEN)$(CHECKMARK) Graphiti is ready$(NC)"; \
			break; \
		fi; \
		echo -e "$(YELLOW)Waiting for Graphiti... ($$timeout seconds remaining)$(NC)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo -e "$(RED)$(ERROR) Graphiti failed to start$(NC)"; \
		exit 1; \
	fi

install-database-local: ## 🗄️ Install database for local development
	@if [ "$(ACTIVE_ENV)" = "development" ]; then \
		echo -e "$(CYAN)Setting up local database (Docker)...$(NC)"; \
		$(MAKE) install-postgres; \
	else \
		echo -e "$(YELLOW)$(WARNING) Local database setup skipped in production mode$(NC)"; \
	fi

# ===========================================
# 🪄 ENVIRONMENT VALIDATION
# ===========================================

check-env-dev: ## ✅ Check development environment configuration
	$(call print_status,Validating development environment...)
	@$(call check_env_file,$(ENV_FILE))
	@echo -e "$(GREEN)$(CHECKMARK) Development environment file validated$(NC)"

check-env-prod: ## ✅ Check production environment configuration
	$(call print_status,Validating production environment...)
	@$(call check_env_file,$(PROD_ENV_FILE))
	@echo -e "$(GREEN)$(CHECKMARK) Production environment file validated$(NC)"

verify-docker: ## 🐳 Verify Docker is available and running
	@$(call verify_docker)

# ===========================================
# 🪄 DOCKER UTILITIES
# ===========================================

docker-build: ## 🔨 Build Docker images
	$(call print_status,Building Docker images...)
	@docker-compose -f $(DOCKER_COMPOSE_FILE) build
	$(call print_success,Docker images built!)

docker-clean: ## 🧹 Clean Docker images and containers
	$(call print_status,Cleaning Docker resources...)
	@echo -e "$(CYAN)Stopping containers...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_FILE) down 2>/dev/null || true
	@docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) down 2>/dev/null || true
	@echo -e "$(CYAN)Removing images...$(NC)"
	@docker rmi automagik-agents:latest 2>/dev/null || echo -e "$(YELLOW)Image not found$(NC)"
	@echo -e "$(CYAN)Pruning system...$(NC)"
	@docker system prune -f
	$(call print_success,Docker cleanup complete!)

setup-prod-volumes: ## 📦 Set up production volumes
	@$(call setup_prod_volumes)

# ===========================================
# 🪄 HELPER FUNCTIONS
# ===========================================

define verify_docker
	@if ! command -v docker >/dev/null 2>&1; then \
		$(call print_error,Docker not found); \
		echo -e "$(YELLOW)💡 Run 'make install-prerequisites' to install Docker$(NC)"; \
		exit 1; \
	fi
	@if ! docker info >/dev/null 2>&1; then \
		$(call print_error,Docker daemon not running); \
		echo -e "$(YELLOW)💡 Start Docker service: sudo systemctl start docker$(NC)"; \
		exit 1; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		$(call print_error,Docker Compose not found); \
		echo -e "$(YELLOW)💡 Run 'make install-prerequisites' to install Docker Compose$(NC)"; \
		exit 1; \
	fi
endef

define setup_prod_volumes
	@echo -e "$(CYAN)Setting up production volumes...$(NC)"
	@docker volume create automagik_postgres_data_prod 2>/dev/null || true
	@docker volume create automagik_logs_prod 2>/dev/null || true
	@echo -e "$(GREEN)$(CHECKMARK) Production volumes ready$(NC)"
endef

define create_systemd_service
	@echo -e "$(CYAN)Creating systemd service file...$(NC)"
	@sudo tee /etc/systemd/system/automagik-agents.service > /dev/null << EOF
[Unit]
Description=Automagik Agents Service
After=network.target

[Service]
Type=simple
User=$(shell whoami)
WorkingDirectory=$(PROJECT_ROOT)
Environment=PATH=$(VENV_PATH)/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$(VENV_PATH)/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8881
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
	@echo -e "$(GREEN)$(CHECKMARK) Systemd service file created$(NC)"
endef

# ===========================================
# 🪄 SERVICE MANAGEMENT
# ===========================================

start: ## 🚀 Start systemd service
	@$(call print_status,Starting systemd service...)
	@if ! systemctl is-enabled automagik-agents >/dev/null 2>&1; then \
		echo -e "$(RED)❌ Service not installed$(NC)"; \
		echo -e "$(YELLOW)💡 Run 'make install-service' first$(NC)"; \
		exit 1; \
	fi
	@sudo systemctl start automagik-agents
	@echo -e "$(GREEN)✅ Service started$(NC)"
	@echo -e "$(CYAN)💡 Check status with 'make status'$(NC)"

stop: ## 🛑 Stop all instances
	@$(call print_status,Stopping all automagik-agents instances...)
	@echo -e "$(CYAN)Stopping systemd service...$(NC)"
	@sudo systemctl stop automagik-agents 2>/dev/null || echo -e "$(YELLOW)⚠️ Service not running$(NC)"
	@echo -e "$(CYAN)Stopping Docker containers...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_FILE) down 2>/dev/null || echo -e "$(YELLOW)⚠️ Docker dev not running$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) down 2>/dev/null || echo -e "$(YELLOW)⚠️ Docker prod not running$(NC)"
	@echo -e "$(CYAN)Stopping development processes...$(NC)"
	@pkill -f "python.*src" 2>/dev/null || echo -e "$(YELLOW)⚠️ No dev processes found$(NC)"
	@echo -e "$(GREEN)✅ All instances stopped$(NC)"

restart: ## 🔄 Restart systemd service
	@$(call print_status,Restarting systemd service...)
	@sudo systemctl restart automagik-agents
	@echo -e "$(GREEN)✅ Service restarted$(NC)"

dev: check-conflicts-dev ## 🛠️ Start development mode
	@$(call print_status,Starting development mode...)
	@$(call check_env_dev)
	@echo -e "$(CYAN)Activating virtual environment...$(NC)"
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo -e "$(RED)❌ Virtual environment not found$(NC)"; \
		echo -e "$(YELLOW)$(SPARKLE) Run 'make install-dev' first$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)$(MAGIC) Starting automagik-agents in development mode...$(NC)"
	@echo -e "$(PURPLE)🔧 Debug mode enabled - breakpoints supported$(NC)"
	@. $(VENV_PATH)/bin/activate && python -m src

docker: check-conflicts-docker ## 🐳 Start Docker development stack
	@$(call print_status,Starting Docker development stack...)
	@$(call verify_docker)
	@$(call check_env_dev)
	@echo -e "$(CYAN)Building images if needed...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_FILE) build
	@echo -e "$(CYAN)Starting services...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_FILE) up -d
	@echo -e "$(GREEN)✅ Docker development stack started$(NC)"
	@echo -e "$(CYAN)💡 View logs with 'make logs'$(NC)"

prod: check-conflicts-prod ## 🏭 Start production Docker stack
	@$(call print_status,Starting production Docker stack...)
	@$(call verify_docker)
	@$(call check_env_prod)
	@echo -e "$(CYAN)Building production images...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) build
	@echo -e "$(CYAN)Setting up production volumes...$(NC)"
	@$(call setup_prod_volumes)
	@echo -e "$(CYAN)Starting production services...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) up -d
	@echo -e "$(GREEN)✅ Production stack started$(NC)"
	@echo -e "$(CYAN)💡 Monitor with 'make status' and 'make health'$(NC)"

# ===========================================
# 🪄 CONFLICT DETECTION
# ===========================================

check-conflicts-dev: ## 🔍 Check for development mode conflicts
	@$(call check_conflicts,"dev","development")

check-conflicts-docker: ## 🔍 Check for Docker development conflicts  
	@$(call check_conflicts,"docker","Docker development")

check-conflicts-prod: ## 🔍 Check for production conflicts
	@$(call check_conflicts,"prod","production")

# ===========================================
# 🪄 CONFLICT RESOLUTION FUNCTIONS
# ===========================================

define check_conflicts
	@echo -e "$(CYAN)Checking for conflicts with $(2) mode...$(NC)"; \
	conflicts=0; \
	port=$$($(call get_port)); \
	if [ -z "$$port" ]; then \
		echo -e "$(RED)❌ Cannot determine port from environment$(NC)"; \
		exit 1; \
	fi; \
	echo -e "$(CYAN)Checking port $$port...$(NC)"; \
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo -e "$(YELLOW)⚠️ Systemd service is running$(NC)"; \
		conflicts=$$((conflicts + 1)); \
	fi; \
	if docker ps --format "table {{.Names}}" | grep -q "automagik-agents-"; then \
		echo -e "$(YELLOW)⚠️ Docker containers are running$(NC)"; \
		docker ps --filter "name=automagik-agents-" --format "table {{.Names}}\t{{.Status}}"; \
		conflicts=$$((conflicts + 1)); \
	fi; \
	if lsof -ti:$$port >/dev/null 2>&1; then \
		pid=$$(lsof -ti:$$port); \
		echo -e "$(YELLOW)⚠️ Port $$port is in use by PID $$pid$(NC)"; \
		ps -p $$pid -o pid,ppid,cmd --no-headers 2>/dev/null || echo "Process details unavailable"; \
		conflicts=$$((conflicts + 1)); \
	fi; \
	if [ $$conflicts -gt 0 ]; then \
		if [ -z "$(FORCE)" ]; then \
			echo ""; \
			echo -e "$(RED)❌ Conflicts detected! Cannot start $(2) mode.$(NC)"; \
			echo ""; \
			echo -e "$(PURPLE)💡 Resolution options:$(NC)"; \
			echo "  $(CYAN)1. Stop conflicts manually:$(NC) make stop"; \
			echo "  $(CYAN)2. Force start (stops conflicts):$(NC) make $(1) FORCE=1"; \
			echo "  $(CYAN)3. Check what's running:$(NC) make status"; \
			echo ""; \
			exit 1; \
		else \
			echo -e "$(PURPLE)🔧 FORCE=1 detected - resolving conflicts...$(NC)"; \
			$(MAKE) stop; \
			echo -e "$(GREEN)✅ Conflicts resolved$(NC)"; \
		fi; \
	else \
		echo -e "$(GREEN)✅ No conflicts detected$(NC)"; \
	fi
endef

define get_port
	@if [ -f "$(ACTIVE_ENV_FILE)" ]; then \
		grep "^AM_PORT=" "$(ACTIVE_ENV_FILE)" | cut -d= -f2 | tr -d ' "'"'"''; \
	else \
		echo "8000"; \
	fi
endef 

# ===========================================
# 🪄 UNINSTALLATION
# ===========================================

uninstall: ## 🗑️ Uninstall Automagik Agents (keeps Docker, Node.js, Python)
	$(call print_status,Uninstalling Automagik Agents...)
	@echo -e "$(YELLOW)⚠️ This will remove automagik-agents services and containers$(NC)"
	@echo -e "$(CYAN)💡 Core dependencies (Docker, Node.js, Python) will be preserved$(NC)"
	@echo ""
	@if [ -z "$(FORCE)" ]; then \
		read -p "Continue with uninstall? [y/N]: " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo -e "$(YELLOW)Uninstall cancelled$(NC)"; \
			exit 0; \
		fi; \
	fi
	@$(MAKE) uninstall-services
	@$(MAKE) uninstall-containers
	@$(MAKE) uninstall-volumes
	@$(MAKE) uninstall-python-env
	@$(MAKE) uninstall-systemd-service
	@echo ""
	$(call print_success,Automagik Agents uninstalled successfully!)
	@echo -e "$(CYAN)💡 Core dependencies preserved: Docker, Node.js, Python$(NC)"

uninstall-force: ## 🗑️ Force uninstall without confirmation
	@$(MAKE) uninstall FORCE=1

uninstall-services: ## 🛑 Stop and remove all Automagik services
	$(call print_status,Stopping Automagik services...)
	@echo -e "$(CYAN)Stopping systemd service...$(NC)"
	@sudo systemctl stop automagik-agents 2>/dev/null || echo -e "$(YELLOW)⚠️ Service not running$(NC)"
	@echo -e "$(CYAN)Stopping Docker containers...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_FILE) down 2>/dev/null || echo -e "$(YELLOW)⚠️ Docker dev not running$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) down 2>/dev/null || echo -e "$(YELLOW)⚠️ Docker prod not running$(NC)"
	@echo -e "$(CYAN)Stopping development processes...$(NC)"
	@pkill -f "python.*src" 2>/dev/null || echo -e "$(YELLOW)⚠️ No dev processes found$(NC)"
	@echo -e "$(GREEN)✅ All services stopped$(NC)"

uninstall-containers: ## 🐳 Remove Docker containers and images
	$(call print_status,Removing Automagik containers and images...)
	@echo -e "$(CYAN)Removing containers...$(NC)"
	@docker rm -f $$(docker ps -aq --filter "name=automagik") 2>/dev/null || echo -e "$(YELLOW)⚠️ No containers to remove$(NC)"
	@echo -e "$(CYAN)Removing images...$(NC)"
	@docker rmi automagik-agents:latest 2>/dev/null || echo -e "$(YELLOW)⚠️ No images to remove$(NC)"
	@docker rmi $$(docker images --filter "reference=automagik*" -q) 2>/dev/null || echo -e "$(YELLOW)⚠️ No additional images found$(NC)"
	@echo -e "$(GREEN)✅ Containers and images removed$(NC)"

uninstall-volumes: ## 📦 Remove Docker volumes (WARNING: This removes all data!)
	$(call print_status,Removing Docker volumes...)
	@echo -e "$(RED)⚠️ WARNING: This will delete all database data!$(NC)"
	@if [ -z "$(FORCE)" ]; then \
		read -p "Delete all data volumes? [y/N]: " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo -e "$(YELLOW)Volume removal cancelled$(NC)"; \
			exit 0; \
		fi; \
	fi
	@echo -e "$(CYAN)Removing volumes...$(NC)"
	@docker volume rm automagik_postgres_data_prod 2>/dev/null || echo -e "$(YELLOW)⚠️ Prod volume not found$(NC)"
	@docker volume rm automagik_logs_prod 2>/dev/null || echo -e "$(YELLOW)⚠️ Logs volume not found$(NC)"
	@docker volume rm $$(docker volume ls --filter "name=automagik" -q) 2>/dev/null || echo -e "$(YELLOW)⚠️ No additional volumes found$(NC)"
	@echo -e "$(GREEN)✅ Volumes removed$(NC)"

uninstall-python-env: ## 🐍 Remove Python virtual environment
	$(call print_status,Removing Python virtual environment...)
	@if [ -d "$(VENV_PATH)" ]; then \
		rm -rf "$(VENV_PATH)"; \
		echo -e "$(GREEN)✅ Virtual environment removed$(NC)"; \
	else \
		echo -e "$(YELLOW)⚠️ Virtual environment not found$(NC)"; \
	fi

uninstall-systemd-service: ## ⚙️ Remove systemd service
	$(call print_status,Removing systemd service...)
	@if systemctl list-unit-files | grep -q automagik-agents; then \
		sudo systemctl disable automagik-agents 2>/dev/null || true; \
		sudo rm -f /etc/systemd/system/automagik-agents.service; \
		sudo systemctl daemon-reload; \
		echo -e "$(GREEN)✅ Systemd service removed$(NC)"; \
	else \
		echo -e "$(YELLOW)⚠️ Systemd service not found$(NC)"; \
	fi

uninstall-clean: ## 🧹 Clean up temporary files and logs
	$(call print_status,Cleaning up temporary files...)
	@echo -e "$(CYAN)Removing logs...$(NC)"
	@rm -rf logs/ || echo -e "$(YELLOW)⚠️ No logs directory found$(NC)"
	@echo -e "$(CYAN)Removing temporary files...$(NC)"
	@rm -rf dev/temp/* || echo -e "$(YELLOW)⚠️ No temp files found$(NC)"
	@echo -e "$(CYAN)Removing cache files...$(NC)"
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo -e "$(GREEN)✅ Cleanup complete$(NC)"

# ===========================================
# 🪄 STATUS DETECTION
# ===========================================