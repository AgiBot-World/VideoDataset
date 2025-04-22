
DIST_DIR = dist

.PHONY: ruff ruff-format dev mypy lint pre-commit build

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
# build
########################################################################################

build: clean
	python -m build -w

########################################################################################
# publish
########################################################################################

publish:
	twine upload $(if $(CI),--verbose) --skip-existing ./${DIST_DIR}/*
