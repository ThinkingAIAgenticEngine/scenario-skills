#!/bin/bash
# Revenue Forecast Model CLI - isolated setup
# Usage: bash setup.sh [--mirror|--verify]

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SKILL_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
echo "📦 Revenue Forecast Model CLI — Setup"
echo "   Skill directory: $SKILL_DIR"

if [ "${1:-}" = "--verify" ]; then
    echo ""
    echo "🔍 Verifying Python dependencies..."
    if [ ! -x "$VENV_PYTHON" ]; then
        echo "   ❌ Virtual environment not found: $VENV_DIR"
        exit 1
    fi
    "$VENV_PYTHON" -c "import numpy, scipy; print(f'   ✅ numpy {numpy.__version__}; scipy {scipy.__version__}')"
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "   ❌ Python 3 not found. Install Python 3.8+ first."
    exit 1
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo "   Creating isolated environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

echo ""
echo "📥 Installing dependencies (numpy, scipy)..."
echo "   Python: $("$VENV_PYTHON" --version)"
if [ "${1:-}" = "--mirror" ]; then
    "$VENV_PYTHON" -m pip install \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        -r "$SCRIPT_DIR/requirements.txt"
else
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

echo ""
echo "🔍 Verifying installation..."
"$VENV_PYTHON" -c "
import numpy as np
import scipy
print(f'   ✅ numpy {np.__version__}')
print(f'   ✅ scipy {scipy.__version__}')
"

echo ""
echo "🎉 Setup complete! Run a quick test:"
echo "   \"$VENV_PYTHON\" \"$SCRIPT_DIR/forecast.py\" --help"
