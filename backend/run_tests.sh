#!/bin/bash
cd /home/tulkasubuntu/01-sigpi/backend
export PYTEST_RUNNING=true
export DJANGO_SETTINGS_MODULE=config.settings.base
.venv-linux/bin/python -m pytest apps/accounts/tests/ -v --tb=short --no-header 2>&1 | tail -80
