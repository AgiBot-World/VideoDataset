# 确保同一目标内的所有命令在同一个Shell会话中执行，避免环境激活状态丢失
.ONESHELL:
SHELL = /bin/bash
CONDA = /opt/conda/bin/conda
CONDA_ENV = agibot
CONDA_ENV_PYTHON = /opt/conda/envs/$(CONDA_ENV)/bin/python
DIST_DIR = dist

.PHONY: ruff ruff-format dev conda-create conda-activate conda-clean prerequisites lint pre-commit build

########################################################################################
# Development Environment Management
########################################################################################

install:
	pip install -e .

# Prepare the development environment and activate it
dev:
	source "$$($(CONDA) info --base)/etc/profile.d/conda.sh" \
	&& conda activate $(CONDA_ENV) \
	&& if [ "$(CI)" != "true" ] && command -v pre-commit >/dev/null 2>&1; then pre-commit install; fi \
	&& exec bash


########################################################################################
# Lint and pre-commit
########################################################################################

ruff:
	ruff check .

ruff-format:
	ruff format --check .

lint: ruff ruff-format

pre-commit:
	pre-commit run --all-files --hook-stage manual

########################################################################################
# build
########################################################################################

build:
	$(CONDA_ENV_PYTHON) -m build $(if $(CI),-v)

########################################################################################
# publish
########################################################################################

publish:
	twine upload $(if $(CI),--verbose) --skip-existing ./${DIST_DIR}/*
