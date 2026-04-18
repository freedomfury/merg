SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := test

VERSION := $(shell grep '^version = ' pyproject.toml | cut -d'"' -f2)

.PHONY: venv lint tests test build deploy clean

venv:
	uv sync

lint:
	uv tool run ruff check merg/ tests/

tests:
	uv run pytest tests/ -v

test: lint tests

build:
	uv build

deploy: test
	git diff --quiet && git diff --cached --quiet || { echo "Error: uncommitted changes — commit or stash before deploying"; exit 1; }
	git tag v$(VERSION)
	git push origin v$(VERSION)

clean:
	rm -rf dist/ .pytest_cache/ __pycache__ merg/__pycache__ tests/__pycache__ merg/*.egg-info
