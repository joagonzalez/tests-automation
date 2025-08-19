# Makefile for Benchmark Analyzer
# ==================================

# Variables
PYTHON := python
UV := uv
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := benchmark-analyzer
VENV_DIR := .venv
SRC_DIR := benchmark_analyzer
API_DIR := api
TESTS_DIR := tests
INFRA_DIR := infrastructure

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help: ## Display this help message
	@echo "$(BLUE)Benchmark Analyzer Development Commands$(NC)"
	@echo "======================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Environment Setup
.PHONY: install-uv
install-uv: ## Install uv package manager
	@echo "$(BLUE)Installing uv...$(NC)"
	pip install uv

.PHONY: setup
setup: ## Set up development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@$(UV) venv $(VENV_DIR)
	@$(UV) pip install -e ".[dev]"
	@echo "$(GREEN)Development environment ready!$(NC)"

.PHONY: install
install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@$(UV) pip install -e ".[dev]"

.PHONY: install-prod
install-prod: ## Install production dependencies only
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	@$(UV) pip install -e .

.PHONY: update
update: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	@$(UV) pip install --upgrade -e ".[dev]"

# Development Tools
.PHONY: format
format: ## Format code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(UV) run ruff format $(SRC_DIR) $(API_DIR) $(TESTS_DIR)

.PHONY: lint
lint: ## Lint code with ruff
	@echo "$(BLUE)Linting code...$(NC)"
	@$(UV) run ruff check $(SRC_DIR) $(API_DIR) $(TESTS_DIR)

.PHONY: lint-fix
lint-fix: ## Fix linting issues automatically
	@echo "$(BLUE)Fixing linting issues...$(NC)"
	@$(UV) run ruff check --fix $(SRC_DIR) $(API_DIR) $(TESTS_DIR)

.PHONY: typecheck
typecheck: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	@$(UV) run mypy $(SRC_DIR) $(API_DIR)

.PHONY: check
check: lint typecheck ## Run all code quality checks
	@echo "$(GREEN)All checks passed!$(NC)"

# Testing
.PHONY: test
test: ## Run tests with pytest
	@echo "$(BLUE)Running tests...$(NC)"
	@$(UV) run pytest

.PHONY: test-verbose
test-verbose: ## Run tests with verbose output
	@echo "$(BLUE)Running tests (verbose)...$(NC)"
	@$(UV) run pytest -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	@$(UV) run pytest --cov --cov-report=html --cov-report=term

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(UV) run pytest -m "unit"

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	@$(UV) run pytest -m "integration"

# Application Commands
.PHONY: cli
cli: ## Run the CLI application
	@echo "$(BLUE)Starting CLI...$(NC)"
	@$(UV) run benchmark-analyzer --help

.PHONY: api
api: ## Run the API server
	@echo "$(BLUE)Starting API server...$(NC)"
	@set -a && . ./.env && set +a && $(UV) run benchmark-api

.PHONY: api-dev
api-dev: ## Run the API server in development mode
	@echo "$(BLUE)Starting API server (development)...$(NC)"
	@$(UV) run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Database Operations
.PHONY: db-init
db-init: ## Initialize database
	@echo "$(BLUE)Initializing database...$(NC)"
	@if [ -f .env ]; then set -a && . ./.env && set +a && $(UV) run benchmark-analyzer db init; else $(UV) run benchmark-analyzer db init; fi

.PHONY: db-status
db-status: ## Show database status
	@echo "$(BLUE)Database status:$(NC)"
	@set -a && . ./.env && set +a && $(UV) run benchmark-analyzer db status

.PHONY: db-clean
db-clean: ## Clean database (WARNING: Deletes all data)
	@echo "$(YELLOW)WARNING: This will delete all data!$(NC)"
	@set -a && . ./.env && set +a && $(UV) run benchmark-analyzer db clean

.PHONY: db-backup
db-backup: ## Create database backup
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	@set -a && . ./.env && set +a && $(UV) run benchmark-analyzer db backup backups/backup_$(shell date +%Y%m%d_%H%M%S).sql

# Infrastructure
.PHONY: infra-up
infra-up: ## Start infrastructure services
	@echo "$(BLUE)Starting infrastructure services...$(NC)"
	@$(DOCKER_COMPOSE) -f $(INFRA_DIR)/docker-compose.yml up -d

.PHONY: infra-down
infra-down: ## Stop infrastructure services
	@echo "$(BLUE)Stopping infrastructure services...$(NC)"
	@$(DOCKER_COMPOSE) -f $(INFRA_DIR)/docker-compose.yml down

.PHONY: infra-logs
infra-logs: ## Show infrastructure logs
	@echo "$(BLUE)Infrastructure logs:$(NC)"
	@$(DOCKER_COMPOSE) -f $(INFRA_DIR)/docker-compose.yml logs -f

.PHONY: infra-restart
infra-restart: ## Restart infrastructure services
	@echo "$(BLUE)Restarting infrastructure services...$(NC)"
	@$(DOCKER_COMPOSE) -f $(INFRA_DIR)/docker-compose.yml restart

.PHONY: infra-build
infra-build: ## Build infrastructure services
	@echo "$(BLUE)Building infrastructure services...$(NC)"
	@$(DOCKER_COMPOSE) -f $(INFRA_DIR)/docker-compose.yml build

.PHONY: infra-pull
infra-pull: ## Pull infrastructure images
	@echo "$(BLUE)Pulling infrastructure images...$(NC)"
	@$(DOCKER_COMPOSE) -f $(INFRA_DIR)/docker-compose.yml pull

# Load sample data
sample-data:
	@echo "$(BLUE)Loading sample data...$(NC)"
	sh ./examples/import_all_examples.sh


# Cleaning
.PHONY: clean
clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@rm -rf .mypy_cache/
	@rm -rf .ruff_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type f -name "coverage.xml" -delete
	@find . -type f -name "*.cover" -delete

.PHONY: clean-all
clean-all: clean ## Clean everything including virtual environment
	@echo "$(BLUE)Cleaning everything...$(NC)"
	@rm -rf $(VENV_DIR)
	@rm -rf .venv

# Utility Commands
.PHONY: version
version: ## Show version information
	@echo "$(BLUE)Version information:$(NC)"
	@$(UV) run $(PYTHON) -c "import benchmark_analyzer; print(f'Benchmark Analyzer: {benchmark_analyzer.__version__}')" 2>/dev/null || echo "Package not installed"
	@$(UV) --version
	@$(PYTHON) --version

.PHONY: env-info
env-info: ## Show environment information
	@echo "$(BLUE)Environment information:$(NC)"
	@$(UV) run benchmark-analyzer config-info

.PHONY: example-query
example-query: ## Run example query commands
	@echo "$(BLUE)Running example queries...$(NC)"
	@$(UV) run benchmark-analyzer query test-runs --limit 5
	@$(UV) run benchmark-analyzer query test-types
