#!/bin/bash
# SIGPI backend test runner — convenience wrapper for WSL/Linux venv
cd "$(dirname "$0")/backend"
.venv-linux/bin/python -m pytest apps/ "$@"
