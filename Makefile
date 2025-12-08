.PHONY: clean deepclean install dev prerequisites mypy ruff ruff-format pyproject-fmt codespell lint pre-commit test-run test build publish doc-watch doc-build doc-coverage doc
########################################################################################
# Variables
########################################################################################

# Documentation target directory, will be adapted to specific folder for readthedocs.
PUBLIC_DIR := $(shell [ "$$READTHEDOCS" = "True" ] && echo "$${READTHEDOCS_OUTPUT}html" || echo "public")

# Determine the Python version used by pipx.
PIPX_PYTHON_VERSION := $(shell `pipx environment --value PIPX_DEFAULT_PYTHON` -c "from sys import version_info; print(f'{version_info.major}.{version_info.minor}')")

# Use pipenv when not in CI environment and pipenv command exists.
PIPRUN := $(shell command -v pipenv > /dev/null 2>&1 && echo pipenv run)

########################################################################################
# Development Environment Management
########################################################################################

# Remove common intermediate files.
clean:
	-rm -rf \
		$(PUBLIC_DIR) \
		.coverage \
		.mypy_cache \
		.pdm-build \
		.pdm-python \
		.pytest_cache \
		.ruff_cache \
		Pipfile* \
		__pypackages__ \
		build \
		coverage.xml \
		dist
	find . -name '*.egg-info' -print0 | xargs -0 rm -rf
	find . -name '*.pyc' -print0 | xargs -0 rm -f
	find . -name '*.swp' -print0 | xargs -0 rm -f
	find . -name '.DS_Store' -print0 | xargs -0 rm -f
	find . -name '__pycache__' -print0 | xargs -0 rm -rf

# Remove pre-commit hook, virtual environment alongside intermediate files.
deepclean: clean
	if command -v pre-commit > /dev/null 2>&1; then pre-commit uninstall; fi
	if command -v pipenv --venv >/dev/null 2>&1 ; then PIPENV_IGNORE_VIRTUALENVS=1 pipenv --rm; fi

# Create a virtual environment for the project.
venv:
	pipenv --site-packages
	pipenv run pip install --upgrade pip

# Install the package in editable mode with specific optional dependencies.
install-%: venv
	${PIPRUN} pip install -e .[$*]

# Install the package in editable mode.
install: venv
	${PIPRUN} pip install -e .

# Install the package in editable mode with specific optional dependencies.
dev-%: venv
	${PIPRUN} pip install -e . `echo $* | tr ',' ' ' | sed 's/\([^ ]*\)/--group \1/g'`


# Prepare the development environment.
# Install the package in editable mode with all optional dependencies and pre-commit hook.
dev: install
	${PIPRUN} pip install -e . --group test --group doc --group lint
	if [ "$(CI)" != "true" ] && command -v pre-commit > /dev/null 2>&1; then pre-commit install; fi

# Install standalone tools
prerequisites:
	pipx list --short | grep -q "check-jsonschema 0.35.0" || pipx install --force check-jsonschema==0.35.0
	pipx list --short | grep -q "codespell 2.4.1" || pipx install --force codespell[toml]==2.4.1
	pipx list --short | grep -q "pipenv 2025.0.4" || pipx install --force pipenv==2025.0.4
	pipx list --short | grep -q "pre-commit 4.5.0" || pipx install --force pre-commit==4.5.0
	pipx list --short | grep -q "pyproject-fmt 2.6.0" || pipx install --force pyproject-fmt==2.6.0
	pipx list --short | grep -q "ruff 0.14.8" || pipx install --force ruff==0.14.8
	pipx list --short | grep -q "watchfiles 1.1.1" || pipx install --force watchfiles==1.1.1
	pipx list --short | grep -q "twine 6.0.1" || pipx install --force twine==6.0.1

########################################################################################
# Lint and pre-commit
########################################################################################

# Check lint with mypy.
mypy:
	${PIPRUN} python -m mypy . --html-report $(PUBLIC_DIR)/reports/mypy

# Lint with ruff.
ruff:
	ruff check .

# Format with ruff.
ruff-format:
	ruff format --check .

# Check lint with pyproject-fmt.
pyproject-fmt:
	pyproject-fmt pyproject.toml

# Check lint with codespell.
codespell:
	codespell

# Check jsonschema with check-jsonschema.
check-jsonschema:
	check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/*.yml
	check-jsonschema --builtin-schema vendor.renovate --regex-variant nonunicode .renovaterc.json

# Check lint with all linters.
lint: mypy ruff ruff-format pyproject-fmt codespell check-jsonschema

# Run pre-commit with autofix against all files.
pre-commit:
	pre-commit run --all-files --hook-stage manual

########################################################################################
# Test
########################################################################################

# Clean and run test with coverage.
test-run:
	${PIPRUN} python -m coverage erase
	${PIPRUN} python -m coverage run -m pytest

# Generate coverage report for terminal and xml.
test: test-run
	${PIPRUN} python -m coverage report
	${PIPRUN} python -m coverage xml

########################################################################################
# Package
########################################################################################

# Build the package.
build:
	python -m build

# Publish the package.
publish:
	twine upload dist/*

########################################################################################
# Documentation
########################################################################################

# Generate documentation with auto build when changes happen.
doc-watch:
	${PIPRUN} python -m http.server --directory public &
	watchfiles "make doc-build" docs src README.md

# Build documentation only from src.
doc-build:
	${PIPRUN} python -m sphinx --fail-on-warning --write-all docs $(PUBLIC_DIR)

# Generate html coverage reports with badge.
doc-coverage: test-run
	${PIPRUN} python -m coverage html -d $(PUBLIC_DIR)/reports/coverage
	${PIPRUN} bash scripts/generate-coverage-badge.sh $(PUBLIC_DIR)/_static/badges

# Generate all documentation with reports.
doc: doc-build mypy doc-coverage

########################################################################################
# End
########################################################################################
