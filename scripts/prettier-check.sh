#!/usr/bin/env bash
# Pre-commit prettier check — runs only on the staged frontend files
# (pre-commit passes repo-root-relative filenames as "$@").
#
# Uses the nvm Linux node binary directly: npx shims resolve to Windows
# cmd.exe via WSL interop and crash on UNC paths.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
exec node frontend/node_modules/prettier/bin/prettier.cjs --check "$@"
