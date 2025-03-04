.PHONY: ruff ruff-format
########################################################################################
# Variables
########################################################################################


########################################################################################
# Development Environment Management
########################################################################################

# Prepare the development environment.
# Install the package in editable mode with all optional dependencies and pre-commit hook.
dev:
	if [ "$(CI)" != "true" ] && command -v pre-commit > /dev/null 2>&1; then pre-commit install; fi

# Install standalone tools
prerequisites:
	pipx list --short | grep -q "pre-commit 4.1.0" || pipx install --force pre-commit==4.1.0
	pipx list --short | grep -q "ruff 0.9.3" || pipx install --force ruff==0.9.3
	pipx list --short | grep -q "pdm 2.22.3" || pipx install --force pdm==2.22.3

########################################################################################
# Lint and pre-commit
########################################################################################

# Lint with ruff.
ruff:
	ruff check .

# Format with ruff.
ruff-format:
	ruff format --check .

# Check lint with all linters.
lint: ruff ruff-format

# Run pre-commit with autofix against all files.
pre-commit:
	pre-commit run --all-files --hook-stage manual

########################################################################################
# build
########################################################################################

build:
	pdm build $(if $(CI),-v)
