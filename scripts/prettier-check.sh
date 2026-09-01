#!/usr/bin/env bash
# Pre-commit prettier check — runs only on the staged frontend files
# (pre-commit passes repo-root-relative filenames as "$@").
#
# Uses the nvm Linux node binary directly: npx shims resolve to Windows
# cmd.exe via WSL interop and crash on UNC paths.
set -euo pipefail
cd /home/tulkasubuntu/01-sigpi
exec ~/.nvm/versions/node/v24.17.0/bin/node frontend/node_modules/prettier/bin/prettier.cjs --check "$@"
