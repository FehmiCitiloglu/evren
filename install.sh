#!/usr/bin/env bash
# EVREN CLI & Agent — Unix/Linux/macOS Installer
set -e

# Change directory to script location
cd "$(dirname "$0")"

# Execute Python installer
if command -v python3 >/dev/null 2>&1; then
    exec python3 install.py "$@"
elif command -v python >/dev/null 2>&1; then
    exec python install.py "$@"
else
    echo "Error: Python 3 is required but not found in PATH." >&2
    echo "Please install Python 3.10+ (or 'brew install python' / 'sudo apt install python3')." >&2
    exit 1
fi
