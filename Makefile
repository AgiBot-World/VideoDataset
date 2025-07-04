DIST_DIR = dist
SDK_LIB_DIR = /workspace/Video_Codec_SDK_12.1.14/Lib/linux/stubs/x86_64
SYSTEM_LIB_DIR = /usr/lib/x86_64-linux-gnu

.PHONY: ruff ruff-format dev mypy lint pre-commit build ensure-lib

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

install:
	pip install -e .

# Prepare the development environment and activate it
dev:
	if [ "$(CI)" != "true" ] && command -v pre-commit >/dev/null 2>&1; then pre-commit install; fi


########################################################################################
# Lint and pre-commit
########################################################################################

mypy:
	mypy .

ruff:
	ruff check .

ruff-format:
	ruff format --check .

lint: ruff ruff-format mypy

pre-commit:
	pre-commit run --all-files --hook-stage manual

########################################################################################
# Test
########################################################################################

# Clean and run test with coverage.
test:
	python -m coverage erase
	python -m coverage run -m pytest

########################################################################################
# build
########################################################################################

ensure-lib:
	@echo "Checking and copying NVIDIA libraries..."
	@if [ ! -f "$(SYSTEM_LIB_DIR)/libnvcuvid.so.1" ] && [ -f "$(SDK_LIB_DIR)/libnvcuvid.so" ]; then \
		echo "Copying libnvcuvid.so to $(SYSTEM_LIB_DIR)"; \
		sudo cp "$(SDK_LIB_DIR)/libnvcuvid.so" "$(SYSTEM_LIB_DIR)/libnvcuvid.so.1"; \
	fi
	@echo "Library check completed."

build: clean ensure-lib
	python -m build -w

########################################################################################
# publish
########################################################################################

publish:
	twine upload $(if $(CI),--verbose) --skip-existing ${DIST_DIR}/*

########################################################################################
# pyi
########################################################################################
pyi:
	pip install -e . pybind11-stubgen
	pybind11-stubgen videodataset._decoder -o src --ignore-all-errors

########################################################################################
# docs
########################################################################################

SPHINX_BUILD = sphinx-build
SPHINX_AUTOBUILD = sphinx-autobuild
SOURCEDIR = docs
BUILDDIR = docs/_build/html
SPHINX_OPTS = -T -c $(SOURCEDIR) $(SOURCEDIR) $(BUILDDIR)
KEEP_GOING = --keep-going
NITPICKY = -n
LINKCHECK = -b linkcheck

docs-prepare:
	pip install -e .[docs]

docs-generate:
	$(SPHINX_BUILD) $(KEEP_GOING) $(SPHINX_OPTS) $(POSARGS)

docs-serve:
	pip install sphinx-autobuild
	$(SPHINX_AUTOBUILD) $(SPHINX_OPTS) $(POSARGS)

docs-check:
	$(SPHINX_BUILD) $(NITPICKY) $(SPHINX_OPTS) $(POSARGS)

docs-linkcheck:
	$(SPHINX_BUILD) $(LINKCHECK) $(SPHINX_OPTS) $(POSARGS)

########################################################################################
# Benchmark
########################################################################################

# or min:1% or mean:0.001 or mean:1%
BENCHMARK_FAIL ?= mean:5%
BENCHMARK_MIN_ROUND ?= 30
BENCHMARK_MAX_KEEP ?= 9
BENCHMARK_WARMUP ?= on
BENCHMARK_WARMUP_ITERATIONS ?= 4

benchmark:
	@pytest --benchmark-only --benchmark-autosave --benchmark-sort=name \
	--benchmark-cprofile=function_name \
	--benchmark-cprofile-top=10 \
	--benchmark-min-rounds=$(BENCHMARK_MIN_ROUND) \
	--benchmark-warmup=$(BENCHMARK_WARMUP) \
	--benchmark-warmup-iterations=$(BENCHMARK_WARMUP_ITERATIONS) \
	$(if $(shell find .benchmarks -mindepth 2 -print -quit 2>/dev/null), \
		--benchmark-compare-fail="$(BENCHMARK_FAIL)" --benchmark-compare,)

benchmark-histogram:
	pytest-benchmark compare --sort=name --histogram=.benchmarks/histogram

benchmark-clean:
	find .benchmarks/ -name *.json | tail -n 1 | xargs rm

benchmark-keep:
	find .benchmarks/ -name *.json | sort -n | head -n -$(BENCHMARK_MAX_KEEP) | xargs -r rm
