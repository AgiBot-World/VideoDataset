.PHONY: clean deepclean install dev prerequisites mypy ruff ruff-format pyproject-fmt codespell lint pre-commit test build publish
########################################################################################
# Variables
########################################################################################
DIST_DIR = dist
# Documentation target directory, will be adapted to specific folder for readthedocs.
PUBLIC_DIR := $(shell [ "$$READTHEDOCS" = "True" ] && echo "$${READTHEDOCS_OUTPUT}html" || echo "public")

# Determine the Python version used by pipx.
PIPX_PYTHON_VERSION := $(shell `pipx environment --value PIPX_DEFAULT_PYTHON` -c "from sys import version_info; print(f'{version_info.major}.{version_info.minor}')")

########################################################################################
# Development Environment Management
########################################################################################
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
		_skbuild \
		dist
	find . -name '*.egg-info' -print0 | xargs -0 rm -rf
	find . -name '*.pyc' -print0 | xargs -0 rm -f
	find . -name '*.swp' -print0 | xargs -0 rm -f
	find . -name '.DS_Store' -print0 | xargs -0 rm -f
	find . -name '__pycache__' -print0 | xargs -0 rm -rf

# Remove pre-commit hook, virtual environment alongside intermediate files.
deepclean: clean
	if command -v pre-commit > /dev/null 2>&1; then pre-commit uninstall; fi
	if command -v pdm >/dev/null 2>&1 && pdm venv list | grep -q in-project ; then pdm venv remove --yes in-project >/dev/null 2>&1; fi

# Install the package in editable mode with specific optional dependencies.
install-%:
	pdm install --prod --group $*

# Install the package in editable mode with all optional dependencies.
install:
	pdm install --prod

# Install the package in editable mode with specific optional dependencies.
dev-%: install
	pdm install --lockfile pdm.dev.lock --no-default --dev --group $*

# Prepare the development environment.
# Install the package in editable mode with all optional dependencies and pre-commit hook.
dev: install
	pdm install --lockfile pdm.dev.lock --no-default --dev
	if [ "$(CI)" != "true" ] && command -v pre-commit > /dev/null 2>&1; then pre-commit install; fi

# Lock both prod and dev dependencies.
lock:
	pdm lock --prod --group lerobot --update-reuse-installed
	pdm lock --lockfile pdm.dev.lock --no-default --dev --group lerobot --update-reuse-installed

# Install standalone tools
prerequisites:
	pipx list | grep -q "package check-jsonschema 0.33.0" || pipx install --force check-jsonschema==0.33.0
	pipx list | grep -q "package codespell 2.4.1" || pipx install --force codespell[toml]==2.4.1
	pipx list | grep -q "package pdm 2.25.2" || pipx install --force pdm==2.25.2
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
test:
	pdm run coverage erase
	pdm run coverage run -m pytest

########################################################################################
# Package
########################################################################################

# Build the package.
build:
	pdm build --no-sdist

# Publish the package.
publish:
	twine upload $(if $(CI),--verbose) --skip-existing ./${DIST_DIR}/*

########################################################################################
# docs
########################################################################################

SPHINX_BUILD = pdm run sphinx-build
SPHINX_AUTOBUILD = pdm run sphinx-autobuild
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
	pdm install --lockfile pdm.dev.lock --no-default --dev -G dev
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
	pdm run pytest --benchmark-only --benchmark-autosave --benchmark-sort=name \
	--benchmark-cprofile=function_name \
	--benchmark-cprofile-top=10 \
	--benchmark-min-rounds=$(BENCHMARK_MIN_ROUND) -W ignore \
	--benchmark-warmup=$(BENCHMARK_WARMUP) \
	--benchmark-warmup-iterations=$(BENCHMARK_WARMUP_ITERATIONS) \
	$(if $(shell find .benchmarks -mindepth 2 -print -quit 2>/dev/null), \
		--benchmark-compare-fail="$(BENCHMARK_FAIL)" --benchmark-compare,)

benchmark-histogram:
	pdm run pytest-benchmark compare --sort=name --histogram=.benchmarks/histogram

benchmark-clean:
	find .benchmarks/ -name *.json | tail -n 1 | xargs rm

benchmark-keep:
	find .benchmarks/ -name *.json | sort -n | head -n -$(BENCHMARK_MAX_KEEP) | xargs -r rm
