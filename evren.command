#!/bin/bash
# evren masaüstü uygulaması başlatıcısı (macOS)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -f ".venv/bin/evren" ]; then
    exec .venv/bin/evren gui
elif command -v evren >/dev/null 2>&1; then
    exec evren gui
else
    exec python3 -m evren_agent.ui
fi
