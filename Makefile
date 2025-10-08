# Simple developer workflow for install, linting, formatting, type-checking, testing, and debugging

SHELL := bash
.DEFAULT_GOAL := help

# Directories
SRC_DIR := src
TESTS_DIR := tests

# Tools (override with e.g. `make PYTEST='uv run pytest' test`)
UV ?= uv
NPX ?= npx
PYTEST ?= uv run pytest
RUFF ?= uv run ruff
MYPY ?= uv run mypy
BLACK ?= uv run black

.PHONY: help install-dev sync run debug test coverage lint lint-fix typecheck fmt fmt-ruff fmt-all check clean

help: ## Show available make targets
	@echo "Available targets:"
	@echo "  install-dev - Install dev deps (uv pip -e .[dev])."
	@echo "  sync       - Create venv and install using uv sync."
	@echo "  run        - Run the MCP server (uv run)."
	@echo "  debug      - Launch MCP Inspector for the server."
	@echo "  test       - Run pytest (with coverage via pyproject)."
	@echo "  coverage   - Run pytest with explicit coverage flags."
	@echo "  lint       - Run Ruff lint checks."
	@echo "  lint-fix   - Run Ruff and apply autofixes."
	@echo "  typecheck  - Run mypy type checks."
	@echo "  fmt        - Format code with Black."
	@echo "  fmt-ruff   - Format code with Ruff formatter."
	@echo "  fmt-all    - Black format + Ruff autofix."
	@echo "  check      - Lint, typecheck, and tests."
	@echo "  clean      - Remove caches and build artifacts."
	@echo
	@echo "Tip: prepend tools with 'uv run' if you use uv, e.g.:"
	@echo "  make PYTEST='uv run pytest' RUFF='uv run ruff' MYPY='uv run mypy' BLACK='uv run black'"
	@echo "Or set 'UV=uv' to use uv subcommands for install/run targets."

install-dev: ## Install dev tools (ruff, black, mypy, pytest, coverage)
	$(UV) pip install -e ".[dev]"

sync: ## Create venv and install from pyproject/uv.lock
	$(UV) sync

run: ## Run the MCP server via uv
	$(UV) run $(SRC_DIR)/mcp_server_dash.py

debug: ## Launch MCP Inspector to run the server
	$(NPX) @modelcontextprotocol/inspector $(UV) run $(SRC_DIR)/mcp_server_dash.py

test: ## Run tests
	$(PYTEST)

coverage: ## Run tests with explicit coverage flags
	$(PYTEST) -q --cov=$(SRC_DIR) --cov-report=term-missing

lint: ## Lint with Ruff (no fixes)
	$(RUFF) check .

lint-fix: ## Lint with Ruff and apply fixes
	$(RUFF) check --fix .

typecheck: ## Static type checks
	$(MYPY) $(SRC_DIR)

fmt: ## Format code with Black
	$(BLACK) .

fmt-ruff: ## Format code with Ruff formatter
	$(RUFF) format .

fmt-all: ## Run Black format and Ruff autofix
	$(BLACK) .
	$(RUFF) check --fix .

check: ## Run lint, typecheck, and tests
	$(MAKE) fmt-all
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

clean: ## Remove caches and artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ .coverage htmlcov
