#!/usr/bin/env bash
set -euo pipefail

# Shortcut: aktifkan venv & buka menu
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

omdl menu
