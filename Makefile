.PHONY: clean deepclean install dev prerequisites mypy ruff ruff-format pyproject-fmt codespell lint pre-commit test build publish
########################################################################################
# Variables
########################################################################################

# Documentation target directory, will be adapted to specific folder for readthedocs.
PUBLIC_DIR := $(shell [ "$$READTHEDOCS" = "True" ] && echo "$${READTHEDOCS_OUTPUT}html" || echo "public")
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
		.pytest_cache \
		.ruff_cache \
		__pypackages__ \
		Pipfile \
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

# Prepare virtualenv
venv:
	@pipenv --site-packages
	@pipenv run pip install --upgrade pip

# Install the package in editable mode with specific optional dependencies.
install-%: venv
	${PIPRUN} pip install -e .[$*]

# Install the package in editable mode with all optional dependencies.
install: venv
	${PIPRUN} pip install -e .

# Install the package in editable mode with all optional dependencies and pre-commit hook
dev-%: venv
	${PIPRUN} pip install -e .[lerobot] --group $*

# Prepare the development environment.
# Install the package in editable mode with all optional dependencies and test group
# Install pre-commit hook
dev: venv
	${PIPRUN} pip install -e .[lerobot] --group test
	if [ "$(CI)" != "true" ] && command -v pre-commit > /dev/null 2>&1; then pre-commit install; fi

# Install standalone tools
prerequisites:
	pipx list | grep -q "package check-jsonschema 0.33.0" || pipx install --force check-jsonschema==0.33.0
	pipx list | grep -q "package codespell 2.4.1" || pipx install --force codespell[toml]==2.4.1
	pipx list | grep -q "pipenv 2025.0.4" || pipx install --force pipenv==2025.0.4
	pipx list | grep -q "package pre-commit 4.2.0" || pipx install --force pre-commit==4.2.0
	pipx list | grep -q "package pyproject-fmt 2.5.1" || pipx install --force pyproject-fmt==2.5.1
	pipx list | grep -q "package ruff 0.11.6" || pipx install --force ruff==0.11.6
	pipx list | grep -q "package watchfiles 1.0.5" || pipx install --force watchfiles==1.0.5


########################################################################################
# Lint and pre-commit
########################################################################################

mypy:
	mypy .

ruff:
	ruff check .

ruff-format:
	ruff format --check .

pyproject-fmt:
	pyproject-fmt pyproject.toml

lint: ruff ruff-format mypy pyproject-fmt

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
	python -m build -w $(if $(CI),-v)

# Publish the package.
publish:
	twine upload $(if $(CI),--verbose) --skip-existing ./dist/*

########################################################################################
# docs
########################################################################################

SPHINX_BUILD = ${PIPRUN} python -m sphinx
SPHINX_AUTOBUILD = ${PIPRUN} sphinx-autobuild
SOURCEDIR = docs
BUILDDIR = docs/_build/html
SPHINX_OPTS = -T -c $(SOURCEDIR) $(SOURCEDIR) $(BUILDDIR)
KEEP_GOING = --keep-going
NITPICKY = -n
LINKCHECK = -b linkcheck

docs-prepare: dev-docs

docs-generate:
	$(SPHINX_BUILD) $(KEEP_GOING) $(SPHINX_OPTS) $(POSARGS)

docs-serve:
	$(SPHINX_AUTOBUILD) $(SPHINX_OPTS) $(POSARGS)

docs-check:
	$(SPHINX_BUILD) $(NITPICKY) $(SPHINX_OPTS) $(POSARGS)

docs-linkcheck:
	$(SPHINX_BUILD) $(LINKCHECK) $(SPHINX_OPTS) $(POSARGS)

########################################################################################
# Benchmark
########################################################################################

# or min:1% or mean:0.001 or mean:1%
BENCHMARK_FAIL ?= min:4%
BENCHMARK_MIN_ROUND ?= 30
BENCHMARK_MAX_KEEP ?= 9
BENCHMARK_WARMUP ?= on
BENCHMARK_WARMUP_ITERATIONS ?= 4

benchmark:
	${PIPRUN} python -m pytest --benchmark-only --benchmark-autosave --benchmark-sort=name \
	--benchmark-cprofile=function_name \
	--benchmark-cprofile-top=10 \
	--benchmark-min-rounds=$(BENCHMARK_MIN_ROUND) -W ignore \
	--benchmark-warmup=$(BENCHMARK_WARMUP) \
	--benchmark-warmup-iterations=$(BENCHMARK_WARMUP_ITERATIONS) \
	$(if $(shell find .benchmarks -mindepth 2 -print -quit 2>/dev/null), \
		--benchmark-compare-fail="$(BENCHMARK_FAIL)" --benchmark-compare,)

benchmark-histogram:
	${PIPRUN} pytest-benchmark compare --sort=name --histogram=.benchmarks/histogram

benchmark-clean:
	find .benchmarks/ -name *.json | tail -n 1 | xargs rm

benchmark-keep:
	find .benchmarks/ -name *.json | sort -n | head -n -$(BENCHMARK_MAX_KEEP) | xargs -r rm
