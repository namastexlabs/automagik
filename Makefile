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
	@echo "                                                                             "
	@echo "                                                                             "
	@echo "     █▓         ████████▓ ██████▓░░██▓     ██▓   ▓▓     ██████▓▓█▓░██▓ ░██▓ "
	@echo "    ███▓ ░██▓   ██▓     ▒██▓   ▒██░███▓   ███▓  ▒██▓   ██▓     ██▓▒██ ██▓   "
	@echo "   ██▓██▓░██▓   ██▓▒██▓ ██▓░██▓ ██░████▓ ████▓  ████▓▒██▓▒████▓██▓▒████▓    "
	@echo "   ██ ░██▒██▓   ██▓░██▓  ██▓   ███▒█▓░████▓▒█▓░██▓ ██▓ ██▓  ██▓▒█▓▒██░██▓   "
	@echo "  ██▓  ██▓ █████▓▓  ██▓   ██████▓ ░█▓  ██▓    ██▓   ██  ███████████▓    ██▓ "
	@echo "                                                                             "
	@echo "                                                                             "
	@echo "$(BOLD_PURPLE)╔═══════════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BOLD_PURPLE)║                        💜 AUTOMAGIK AGENTS                           ║$(NC)"
	@echo "$(BOLD_PURPLE)║                     by Namastex Labs namastex.ai                      ║$(NC)"
	@echo "$(BOLD_PURPLE)╚═══════════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
endef

define print_section
	@echo ""
	@echo "$(PURPLE)$(1)$(NC)"
	@echo "$(PURPLE)$(shell printf '=%.0s' {1..$(shell echo '$(1)' | wc -c)})$(NC)"
endef

define print_status
	@echo -e "$(PURPLE)💜 $(1)$(NC)"
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
.PHONY: install-prerequisites install-prerequisites-linux install-prerequisites-mac
.PHONY: install-prerequisites-debian install-prerequisites-rhel install-prerequisites-fedora install-prerequisites-arch
.PHONY: install-docker-debian install-docker-rhel install-docker-fedora install-docker-arch
.PHONY: install-uv verify-prerequisites
.PHONY: install-python-env install-service install-postgres install-neo4j install-graphiti
.PHONY: install-database-local check-env-dev check-env-prod verify-docker
.PHONY: venv-create venv-clean requirements-update setup-prod-volumes

# ===========================================
# 💜 HELP SYSTEM
# ===========================================
help: ## 💜 Show this help message
	$(call print_banner)
	@echo "$(CYAN)Environment: $(ACTIVE_ENV) (using $(ACTIVE_ENV_FILE))$(NC)"
	@echo ""
	$(call print_section,🚀 Quick Start)
	@echo "  $(PURPLE)make install$(NC)         Auto-detect and install appropriate environment"
	@echo "  $(PURPLE)make install-dev$(NC)     Install development environment"
	@echo "  $(PURPLE)make dev$(NC)             Start in development mode"
	@echo "  $(PURPLE)make docker$(NC)          Start Docker development stack"
	@echo "  $(PURPLE)make prod$(NC)            Start production Docker stack"
	@echo ""
	$(call print_section,🔧 Prerequisites)
	@echo "  $(PURPLE)install-prerequisites$(NC) Install system dependencies (all platforms)"
	@echo "  $(PURPLE)install-uv$(NC)           Install uv Python package manager"
	@echo "  $(PURPLE)verify-prerequisites$(NC) Verify all prerequisites are installed"
	@echo "  $(PURPLE)check-system$(NC)         Check system prerequisites"
	@echo ""
	$(call print_section,📋 Installation)
	@echo "  $(PURPLE)install$(NC)              Auto-detect and install (recommended)"
	@echo "  $(PURPLE)install-dev$(NC)          Development environment (local Python)"
	@echo "  $(PURPLE)install-docker$(NC)       Docker development environment"
	@echo "  $(PURPLE)install-prod$(NC)         Production Docker environment"
	@echo "  $(PURPLE)install-service$(NC)      Systemd service installation"
	@echo ""
	$(call print_section,🗄️ Individual Services)
	@echo "  $(PURPLE)install-postgres$(NC)     PostgreSQL database container"
	@echo "  $(PURPLE)install-neo4j$(NC)        Neo4j graph database (for Graphiti)"
	@echo "  $(PURPLE)install-graphiti$(NC)     Graphiti knowledge graph service"
	@echo "  $(PURPLE)install-python-env$(NC)   Python virtual environment only"
	@echo ""
	$(call print_section,🎛️ Service Management)
	@echo "  $(PURPLE)start$(NC)                Start services (auto-detect mode)"
	@echo "  $(PURPLE)stop$(NC)                 Stop all services"
	@echo "  $(PURPLE)restart$(NC)              Restart services"
	@echo "  $(PURPLE)status$(NC)               Show PM2-style status table"
	@echo "  $(PURPLE)logs$(NC)                 View colorized logs"
	@echo "  $(PURPLE)health$(NC)               Check health of all services"
	@echo ""
	$(call print_section,🛠️ Development)
	@echo "  $(PURPLE)test$(NC)                 Run test suite"
	@echo "  $(PURPLE)lint$(NC)                 Run code linting"
	@echo "  $(PURPLE)format$(NC)               Format code with ruff"
	@echo "  $(PURPLE)requirements-update$(NC)  Update Python dependencies"
	@echo ""
	$(call print_section,🗄️ Database)
	@echo "  $(PURPLE)db-init$(NC)              Initialize database"
	@echo "  $(PURPLE)db-migrate$(NC)           Run database migrations"
	@echo "  $(PURPLE)db-reset$(NC)             Reset database (WARNING: destructive)"
	@echo ""
	$(call print_section,🐳 Docker)
	@echo "  $(PURPLE)docker-build$(NC)         Build Docker images"
	@echo "  $(PURPLE)docker-clean$(NC)         Clean Docker images and containers"
	@echo ""
	$(call print_section,🧹 Maintenance)
	@echo "  $(PURPLE)clean$(NC)                Clean temporary files"
	@echo "  $(PURPLE)reset$(NC)                Full reset (WARNING: destructive)"
	@echo "  $(PURPLE)venv-clean$(NC)           Remove virtual environment"
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
# 💜 PREREQUISITE INSTALLATION SYSTEM
# ===========================================

# OS detection variables
UNAME_S := $(shell uname -s)
DISTRO := $(shell lsb_release -si 2>/dev/null || echo "Unknown")

install-prerequisites: ## 🔧 Install system prerequisites for all platforms
	$(call print_banner)
	$(call print_status,Installing system prerequisites...)
	@echo "$(CYAN)Detected OS: $(UNAME_S)$(NC)"
	@if [ "$(DISTRO)" != "Unknown" ]; then \
		echo "$(CYAN)Distribution: $(DISTRO)$(NC)"; \
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
	$(call print_success,System prerequisites installation complete!)
	@echo "$(CYAN)💡 Run 'make install-dev' to set up the Python environment$(NC)"

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
		echo "$(YELLOW)💡 Please install manually: python3.12, docker, docker-compose, make, curl, jq, ccze, git$(NC)"; \
		exit 1; \
	fi

install-prerequisites-debian: ## 📦 Install Debian/Ubuntu prerequisites
	$(call print_status,Installing Debian/Ubuntu packages...)
	@echo "$(CYAN)Updating package lists...$(NC)"
	@sudo apt-get update -qq
	@echo "$(CYAN)Installing core packages...$(NC)"
	@sudo apt-get install -y \
		python3 python3-pip python3-venv python3-dev \
		make curl jq git build-essential \
		software-properties-common apt-transport-https ca-certificates gnupg lsb-release
	@echo "$(CYAN)Installing colorization tools...$(NC)"
	@sudo apt-get install -y ccze multitail || echo "$(YELLOW)$(WARNING) ccze/multitail not available in repos$(NC)"
	@echo "$(CYAN)Installing optional development tools...$(NC)"
	@sudo apt-get install -y htop ncdu tree || echo "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo apt-get install -y postgresql-client || echo "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-debian

install-prerequisites-rhel: ## 📦 Install RHEL/CentOS prerequisites
	$(call print_status,Installing RHEL/CentOS packages...)
	@echo "$(CYAN)Installing core packages...$(NC)"
	@sudo yum install -y epel-release || echo "$(YELLOW)$(WARNING) EPEL repository not available$(NC)"
	@sudo yum install -y \
		python3 python3-pip python3-devel \
		make curl jq git gcc gcc-c++ \
		ca-certificates
	@echo "$(CYAN)Installing colorization tools...$(NC)"
	@sudo yum install -y ccze multitail || echo "$(YELLOW)$(WARNING) ccze/multitail not available in repos$(NC)"
	@echo "$(CYAN)Installing optional development tools...$(NC)"
	@sudo yum install -y htop ncdu tree || echo "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo yum install -y postgresql || echo "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-rhel

install-prerequisites-fedora: ## 📦 Install Fedora prerequisites
	$(call print_status,Installing Fedora packages...)
	@echo "$(CYAN)Installing core packages...$(NC)"
	@sudo dnf install -y \
		python3 python3-pip python3-devel \
		make curl jq git gcc gcc-c++ \
		ca-certificates
	@echo "$(CYAN)Installing colorization tools...$(NC)"
	@sudo dnf install -y ccze multitail || echo "$(YELLOW)$(WARNING) ccze/multitail not available in repos$(NC)"
	@echo "$(CYAN)Installing optional development tools...$(NC)"
	@sudo dnf install -y htop ncdu tree || echo "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo dnf install -y postgresql || echo "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-fedora

install-prerequisites-arch: ## 📦 Install Arch Linux prerequisites
	$(call print_status,Installing Arch Linux packages...)
	@echo "$(CYAN)Updating package database...$(NC)"
	@sudo pacman -Sy
	@echo "$(CYAN)Installing core packages...$(NC)"
	@sudo pacman -S --noconfirm --needed \
		python python-pip \
		make curl jq git base-devel \
		ca-certificates
	@echo "$(CYAN)Installing colorization tools...$(NC)"
	@sudo pacman -S --noconfirm --needed ccze multitail || echo "$(YELLOW)$(WARNING) ccze/multitail not available$(NC)"
	@echo "$(CYAN)Installing optional development tools...$(NC)"
	@sudo pacman -S --noconfirm --needed htop ncdu tree || echo "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo "$(CYAN)Installing PostgreSQL client...$(NC)"
	@sudo pacman -S --noconfirm --needed postgresql-libs || echo "$(YELLOW)$(WARNING) PostgreSQL client not available$(NC)"
	@$(MAKE) install-docker-arch

install-prerequisites-mac: ## 🍎 Install macOS prerequisites
	$(call print_status,Installing macOS prerequisites...)
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Homebrew...$(NC)"; \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
		echo "$(GREEN)$(CHECKMARK) Homebrew installed$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Homebrew already installed$(NC)"; \
	fi
	@echo "$(CYAN)Updating Homebrew...$(NC)"
	@brew update
	@echo "$(CYAN)Installing core packages...$(NC)"
	@brew install python@3.12 || brew install python@3.11 || brew install python3
	@brew install make curl jq git
	@echo "$(CYAN)Installing colorization tools...$(NC)"
	@brew install ccze multitail || echo "$(YELLOW)$(WARNING) ccze/multitail not available$(NC)"
	@echo "$(CYAN)Installing optional development tools...$(NC)"
	@brew install htop ncdu tree || echo "$(YELLOW)$(WARNING) Some development tools not available$(NC)"
	@echo "$(CYAN)Installing PostgreSQL client...$(NC)"
	@brew install postgresql || echo "$(YELLOW)$(WARNING) PostgreSQL not available$(NC)"
	@echo "$(CYAN)Installing Docker...$(NC)"
	@brew install --cask docker || echo "$(YELLOW)$(WARNING) Docker installation may require manual setup$(NC)"

# Docker installation for different Linux distributions
install-docker-debian: ## 🐳 Install Docker on Debian/Ubuntu
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker for Debian/Ubuntu...$(NC)"; \
		curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg; \
		echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null; \
		sudo apt-get update -qq; \
		sudo apt-get install -y docker-ce docker-ce-cli containerd.io; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker Compose...$(NC)"; \
		sudo apt-get install -y docker-compose-plugin; \
		echo "$(GREEN)$(CHECKMARK) Docker Compose installed$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker Compose already installed$(NC)"; \
	fi

install-docker-rhel: ## 🐳 Install Docker on RHEL/CentOS
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker for RHEL/CentOS...$(NC)"; \
		sudo yum install -y yum-utils; \
		sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo; \
		sudo yum install -y docker-ce docker-ce-cli containerd.io; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker Compose...$(NC)"; \
		sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$$(uname -s)-$$(uname -m)" -o /usr/local/bin/docker-compose; \
		sudo chmod +x /usr/local/bin/docker-compose; \
		echo "$(GREEN)$(CHECKMARK) Docker Compose installed$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker Compose already installed$(NC)"; \
	fi

install-docker-fedora: ## 🐳 Install Docker on Fedora
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker for Fedora...$(NC)"; \
		sudo dnf -y install dnf-plugins-core; \
		sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo; \
		sudo dnf install -y docker-ce docker-ce-cli containerd.io; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker Compose...$(NC)"; \
		sudo dnf install -y docker-compose-plugin; \
		echo "$(GREEN)$(CHECKMARK) Docker Compose installed$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker Compose already installed$(NC)"; \
	fi

install-docker-arch: ## 🐳 Install Docker on Arch Linux
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(CYAN)Installing Docker for Arch Linux...$(NC)"; \
		sudo pacman -S --noconfirm --needed docker docker-compose; \
		sudo systemctl enable docker; \
		sudo systemctl start docker; \
		sudo usermod -aG docker $$USER; \
		echo "$(GREEN)$(CHECKMARK) Docker installed$(NC)"; \
		echo "$(YELLOW)$(WARNING) Please log out and back in for Docker group membership to take effect$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Docker already installed$(NC)"; \
	fi

install-uv: ## ⚡ Install uv Python package manager
	@if ! command -v uv >/dev/null 2>&1; then \
		$(call print_status,Installing uv Python package manager...); \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "$(GREEN)$(CHECKMARK) uv installed$(NC)"; \
		echo "$(YELLOW)💡 You may need to restart your shell or run: source ~/.bashrc$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) uv already installed$(NC)"; \
	fi

verify-prerequisites: ## ✅ Verify all prerequisites are properly installed
	$(call print_status,Verifying prerequisites installation...)
	@echo ""
	@echo "$(PURPLE)🐍 Python:$(NC)"
	@if python3 --version >/dev/null 2>&1; then \
		version=$$(python3 --version 2>&1); \
		echo "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo "$(RED)$(ERROR) Python 3 not found$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)🐳 Docker:$(NC)"
	@if docker --version >/dev/null 2>&1; then \
		version=$$(docker --version); \
		echo "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) Docker not found$(NC)"; \
	fi
	@if docker-compose --version >/dev/null 2>&1; then \
		version=$$(docker-compose --version); \
		echo "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) Docker Compose not found$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)🔧 Build Tools:$(NC)"
	@if make --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) make installed$(NC)"; \
	else \
		echo "$(RED)$(ERROR) make not found$(NC)"; \
	fi
	@if curl --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) curl installed$(NC)"; \
	else \
		echo "$(RED)$(ERROR) curl not found$(NC)"; \
	fi
	@if jq --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) jq installed$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) jq not found$(NC)"; \
	fi
	@if git --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) git installed$(NC)"; \
	else \
		echo "$(RED)$(ERROR) git not found$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)🎨 Optional Tools:$(NC)"
	@if ccze --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) ccze installed (colorized logs)$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) ccze not found (plain logs)$(NC)"; \
	fi
	@if multitail -V >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) multitail installed$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) multitail not found$(NC)"; \
	fi
	@if htop --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) htop installed$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) htop not found$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)⚡ Package Manager:$(NC)"
	@if uv --version >/dev/null 2>&1; then \
		version=$$(uv --version); \
		echo "$(GREEN)$(CHECKMARK) $$version$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) uv not found$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)🔐 Database Client:$(NC)"
	@if pg_isready --version >/dev/null 2>&1; then \
		echo "$(GREEN)$(CHECKMARK) PostgreSQL client installed$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) PostgreSQL client not found$(NC)"; \
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
	echo -e "$(PURPLE)💜 Mode: $$mode | Docker: $$docker_count | Local: $$local_count | Service: $$service_active$(NC)"

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
# 💜 COLORFUL LOG VIEWING SYSTEM
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
	@echo "$(CYAN)🔍 Detecting log sources...$(NC)"; \
	if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo "$(GREEN)📋 Found systemd service logs$(NC)"; \
		$(call show_service_logs,$(1)); \
	elif docker ps --filter "name=automagik" --format "{{.Names}}" | head -1 | grep -q automagik; then \
		primary_container=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | grep -E "(automagik_agents|automagik-agents)" | head -1); \
		echo "$(GREEN)🐳 Found Docker logs for: $$primary_container$(NC)"; \
		$(call show_docker_logs,$$primary_container,$(1)); \
	elif [ -f "logs/automagik.log" ]; then \
		echo "$(GREEN)📁 Found local log file$(NC)"; \
		$(call show_file_logs,$(1)); \
	else \
		echo "$(YELLOW)$(WARNING) No log sources found$(NC)"; \
		echo "$(CYAN)💡 Available sources: systemd service, docker containers, log files$(NC)"; \
	fi
endef

define detect_and_follow_logs
	@if systemctl is-active automagik-agents >/dev/null 2>&1; then \
		echo "$(GREEN)📋 Following systemd service logs$(NC)"; \
		$(call follow_service_logs); \
	elif docker ps --filter "name=automagik" --format "{{.Names}}" | head -1 | grep -q automagik; then \
		primary_container=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | grep -E "(automagik_agents|automagik-agents)" | head -1); \
		echo "$(GREEN)🐳 Following Docker logs for: $$primary_container$(NC)"; \
		$(call follow_docker_logs,$$primary_container); \
	elif [ -f "logs/automagik.log" ]; then \
		echo "$(GREEN)📁 Following local log file$(NC)"; \
		$(call follow_file_logs); \
	else \
		echo "$(YELLOW)$(WARNING) No log sources found to follow$(NC)"; \
	fi
endef

# Service logs
define show_service_logs
	journalctl -u automagik-agents -n $(1) --no-pager 2>/dev/null | $(call colorize_logs) || \
	echo "$(RED)$(ERROR) Unable to access systemd logs$(NC)"
endef

define follow_service_logs
	journalctl -u automagik-agents -f --no-pager 2>/dev/null | $(call colorize_logs) || \
	echo "$(RED)$(ERROR) Unable to follow systemd logs$(NC)"
endef

# Docker logs
define show_docker_logs
	docker logs --tail $(2) $(1) 2>&1 | $(call colorize_logs) || \
	echo "$(RED)$(ERROR) Unable to access Docker logs for $(1)$(NC)"
endef

define follow_docker_logs
	docker logs -f $(1) 2>&1 | $(call colorize_logs) || \
	echo "$(RED)$(ERROR) Unable to follow Docker logs for $(1)$(NC)"
endef

# File logs
define show_file_logs
	tail -n $(1) logs/automagik.log 2>/dev/null | $(call colorize_logs) || \
	echo "$(RED)$(ERROR) Unable to access log file$(NC)"
endef

define follow_file_logs
	tail -f logs/automagik.log 2>/dev/null | $(call colorize_logs) || \
	echo "$(RED)$(ERROR) Unable to follow log file$(NC)"
endef

# Log colorization with graceful fallback
define colorize_logs
	if command -v ccze >/dev/null 2>&1; then \
		ccze -A; \
	else \
		echo "$(YELLOW)$(WARNING) ccze not available - showing plain logs$(NC)" >&2; \
		cat; \
	fi
endef

# Specific container log viewing
logs-docker: ## 🐳 View Docker container logs (interactive selection)
	@$(call print_status,Docker Container Logs)
	@containers=$$(docker ps --filter "name=automagik" --format "{{.Names}}" | sort); \
	if [ -z "$$containers" ]; then \
		echo "$(RED)$(ERROR) No automagik Docker containers running$(NC)"; \
		exit 1; \
	fi; \
	echo "$(CYAN)Available containers:$(NC)"; \
	i=1; \
	for container in $$containers; do \
		echo "  $$i) $$container"; \
		i=$$((i+1)); \
	done; \
	echo ""; \
	read -p "Select container (1-$$((i-1))): " choice; \
	selected=$$(echo "$$containers" | sed -n "$${choice}p"); \
	if [ -n "$$selected" ]; then \
		echo "$(GREEN)📋 Showing logs for: $$selected$(NC)"; \
		docker logs --tail 100 $$selected 2>&1 | $(call colorize_logs); \
	else \
		echo "$(RED)$(ERROR) Invalid selection$(NC)"; \
	fi

logs-all: ## 📄 View logs from all sources
	@$(call print_status,All Automagik Logs)
	@echo "$(PURPLE)🔍 Checking all log sources...$(NC)"
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
# 💜 INSTALLATION TARGETS
# ===========================================

install: ## 🚀 Auto-detect and install appropriate environment
	@$(call print_status,Auto-detecting installation mode...)
	@if [ -f "$(PROD_ENV_FILE)" ]; then \
		echo "$(CYAN)Production environment detected - installing prod mode$(NC)"; \
		$(MAKE) install-prod; \
	elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
		echo "$(CYAN)Docker available - installing docker mode$(NC)"; \
		$(MAKE) install-docker; \
	else \
		echo "$(CYAN)Standard environment - installing dev mode$(NC)"; \
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
	@echo "$(CYAN)💡 Next steps:$(NC)"
	@echo "  $(PURPLE)make dev$(NC)     Start development server"
	@echo "  $(PURPLE)make test$(NC)    Run test suite"
	@echo "  $(PURPLE)make status$(NC)  Check service status"

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
	@echo "$(CYAN)💡 Next steps:$(NC)"
	@echo "  $(PURPLE)make docker$(NC)  Start Docker stack"
	@echo "  $(PURPLE)make logs$(NC)    View container logs"
	@echo "  $(PURPLE)make status$(NC)  Check container status"

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
	@echo "$(CYAN)💡 Next steps:$(NC)"
	@echo "  $(PURPLE)make prod$(NC)    Start production stack"
	@echo "  $(PURPLE)make health$(NC)  Check service health"
	@echo "  $(PURPLE)make logs$(NC)    View production logs"

install-service: ## ⚙️ Install systemd service (requires install-dev first)
	$(call print_status,Installing systemd service...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo "$(YELLOW)$(WARNING) Development environment not found$(NC)"; \
		echo "$(CYAN)💡 Running install-dev first...$(NC)"; \
		$(MAKE) install-dev; \
	fi
	@$(call create_systemd_service)
	@sudo systemctl daemon-reload
	@sudo systemctl enable automagik-agents
	$(call print_success,Systemd service installed!)
	@echo "$(CYAN)💡 Service commands:$(NC)"
	@echo "  $(PURPLE)sudo systemctl start automagik-agents$(NC)   Start service"
	@echo "  $(PURPLE)sudo systemctl status automagik-agents$(NC)  Check status"
	@echo "  $(PURPLE)make logs$(NC)                               View logs"

# ===========================================
# 💜 PYTHON ENVIRONMENT MANAGEMENT
# ===========================================

install-python-env: ## 🐍 Install Python virtual environment
	$(call print_status,Setting up Python environment...)
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo "$(CYAN)Creating virtual environment...$(NC)"; \
		python3 -m venv $(VENV_PATH); \
		echo "$(GREEN)$(CHECKMARK) Virtual environment created$(NC)"; \
	else \
		echo "$(GREEN)$(CHECKMARK) Virtual environment already exists$(NC)"; \
	fi
	@echo "$(CYAN)Installing dependencies with uv...$(NC)"
	@$(VENV_PATH)/bin/python -m pip install --upgrade pip
	@if command -v uv >/dev/null 2>&1; then \
		. $(VENV_PATH)/bin/activate && uv sync; \
		echo "$(GREEN)$(CHECKMARK) Dependencies installed with uv$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) uv not found, using pip...$(NC)"; \
		$(VENV_PATH)/bin/pip install -e .; \
		echo "$(GREEN)$(CHECKMARK) Dependencies installed with pip$(NC)"; \
	fi

venv-create: install-python-env ## 🐍 Create virtual environment (alias)

venv-clean: ## 🧹 Remove virtual environment
	$(call print_status,Removing virtual environment...)
	@if [ -d "$(VENV_PATH)" ]; then \
		rm -rf "$(VENV_PATH)"; \
		echo "$(GREEN)$(CHECKMARK) Virtual environment removed$(NC)"; \
	else \
		echo "$(YELLOW)$(WARNING) Virtual environment not found$(NC)"; \
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
# 💜 INDIVIDUAL SERVICE INSTALLATION
# ===========================================

install-postgres: ## 🐘 Install PostgreSQL service
	$(call print_status,Installing PostgreSQL...)
	@$(call verify_docker)
	@docker-compose -f $(DOCKER_COMPOSE_FILE) up -d automagik-agents-db
	@echo "$(CYAN)Waiting for PostgreSQL to be ready...$(NC)"
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f $(DOCKER_COMPOSE_FILE) exec -T automagik-agents-db pg_isready -U postgres >/dev/null 2>&1; then \
			echo "$(GREEN)$(CHECKMARK) PostgreSQL is ready$(NC)"; \
			break; \
		fi; \
		echo "$(YELLOW)Waiting for PostgreSQL... ($$timeout seconds remaining)$(NC)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo "$(RED)$(ERROR) PostgreSQL failed to start$(NC)"; \
		exit 1; \
	fi

install-neo4j: ## 🔗 Install Neo4j service (for graphiti profile)
	$(call print_status,Installing Neo4j...)
	@$(call verify_docker)
	@docker-compose -f $(DOCKER_COMPOSE_FILE) --profile graphiti up -d automagik-agents-neo4j
	@echo "$(CYAN)Waiting for Neo4j to be ready...$(NC)"
	@timeout=90; \
	while [ $$timeout -gt 0 ]; do \
		if curl -s http://localhost:7474 >/dev/null 2>&1; then \
			echo "$(GREEN)$(CHECKMARK) Neo4j is ready$(NC)"; \
			break; \
		fi; \
		echo "$(YELLOW)Waiting for Neo4j... ($$timeout seconds remaining)$(NC)"; \
		sleep 3; \
		timeout=$$((timeout - 3)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo "$(RED)$(ERROR) Neo4j failed to start$(NC)"; \
		exit 1; \
	fi

install-graphiti: ## 🕸️ Install Graphiti service (requires Neo4j)
	$(call print_status,Installing Graphiti...)
	@$(call verify_docker)
	@if ! docker ps | grep -q automagik-agents-neo4j; then \
		echo "$(CYAN)Neo4j not running, starting it first...$(NC)"; \
		$(MAKE) install-neo4j; \
	fi
	@docker-compose -f $(DOCKER_COMPOSE_FILE) --profile graphiti up -d automagik-agents-graphiti
	@echo "$(CYAN)Waiting for Graphiti to be ready...$(NC)"
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if curl -s http://localhost:8000/healthcheck >/dev/null 2>&1; then \
			echo "$(GREEN)$(CHECKMARK) Graphiti is ready$(NC)"; \
			break; \
		fi; \
		echo "$(YELLOW)Waiting for Graphiti... ($$timeout seconds remaining)$(NC)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo "$(RED)$(ERROR) Graphiti failed to start$(NC)"; \
		exit 1; \
	fi

install-database-local: ## 🗄️ Install database for local development
	@if [ "$(ACTIVE_ENV)" = "development" ]; then \
		echo "$(CYAN)Setting up local database (Docker)...$(NC)"; \
		$(MAKE) install-postgres; \
	else \
		echo "$(YELLOW)$(WARNING) Local database setup skipped in production mode$(NC)"; \
	fi

# ===========================================
# 💜 ENVIRONMENT VALIDATION
# ===========================================

check-env-dev: ## ✅ Check development environment configuration
	$(call print_status,Validating development environment...)
	@$(call check_env_file,$(ENV_FILE))
	@echo "$(GREEN)$(CHECKMARK) Development environment file validated$(NC)"

check-env-prod: ## ✅ Check production environment configuration
	$(call print_status,Validating production environment...)
	@$(call check_env_file,$(PROD_ENV_FILE))
	@echo "$(GREEN)$(CHECKMARK) Production environment file validated$(NC)"

verify-docker: ## 🐳 Verify Docker is available and running
	@$(call verify_docker)

# ===========================================
# 💜 DOCKER UTILITIES
# ===========================================

docker-build: ## 🔨 Build Docker images
	$(call print_status,Building Docker images...)
	@docker-compose -f $(DOCKER_COMPOSE_FILE) build
	$(call print_success,Docker images built!)

docker-clean: ## 🧹 Clean Docker images and containers
	$(call print_status,Cleaning Docker resources...)
	@echo "$(CYAN)Stopping containers...$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_FILE) down 2>/dev/null || true
	@docker-compose -f $(DOCKER_COMPOSE_PROD_FILE) down 2>/dev/null || true
	@echo "$(CYAN)Removing images...$(NC)"
	@docker rmi automagik-agents:latest 2>/dev/null || echo "$(YELLOW)Image not found$(NC)"
	@echo "$(CYAN)Pruning system...$(NC)"
	@docker system prune -f
	$(call print_success,Docker cleanup complete!)

setup-prod-volumes: ## 📦 Set up production volumes
	@$(call setup_prod_volumes)

# ===========================================
# 💜 HELPER FUNCTIONS
# ===========================================

define verify_docker
	@if ! command -v docker >/dev/null 2>&1; then \
		$(call print_error,Docker not found); \
		echo "$(YELLOW)💡 Run 'make install-prerequisites' to install Docker$(NC)"; \
		exit 1; \
	fi
	@if ! docker info >/dev/null 2>&1; then \
		$(call print_error,Docker daemon not running); \
		echo "$(YELLOW)💡 Start Docker service: sudo systemctl start docker$(NC)"; \
		exit 1; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		$(call print_error,Docker Compose not found); \
		echo "$(YELLOW)💡 Run 'make install-prerequisites' to install Docker Compose$(NC)"; \
		exit 1; \
	fi
endef

define setup_prod_volumes
	@echo "$(CYAN)Setting up production volumes...$(NC)"
	@docker volume create automagik_postgres_data_prod 2>/dev/null || true
	@docker volume create automagik_logs_prod 2>/dev/null || true
	@echo "$(GREEN)$(CHECKMARK) Production volumes ready$(NC)"
endef

define create_systemd_service
	@echo "$(CYAN)Creating systemd service file...$(NC)"
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
	@echo "$(GREEN)$(CHECKMARK) Systemd service file created$(NC)"
endef 