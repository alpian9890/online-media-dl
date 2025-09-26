#!/usr/bin/env bash
clear

set -euo pipefail

# Jalankan dari root repo
if [ ! -f "pyproject.toml" ]; then
  echo "Jalankan skrip ini dari root proyek (online-media-dl/)."
  exit 1
fi

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

echo "Selesai. Aktifkan venv: source .venv/bin/activate"
echo "Coba: omdl --version"

source .venv/bin/activate
