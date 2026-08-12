#!/bin/bash
# SIGPI test runner — runs from repo root using backend pyproject.toml
set -e
cd "$(dirname "$0")"
pytest -c backend/pyproject.toml "$@"
