#!/bin/bash
# ============================================================
# Hermes — 静态检查入口
#
# 依次运行 ruff (linter) 和 mypy (type checker)，
# 任一失败则整体失败。缺失的工具会给出警告但不会阻断。
# ============================================================

set -euo pipefail

echo "===== Hermes Static Check ====="
FAILED=0

# ----------------------------------------------------------
# ruff — fast Python linter
# ----------------------------------------------------------
if command -v ruff &>/dev/null; then
    echo "→ Running ruff..."
    ruff check app/ || FAILED=1
else
    echo "[SKIP] ruff not installed — run: pip install ruff"
fi

# ----------------------------------------------------------
# mypy — static type checker
# ----------------------------------------------------------
if command -v mypy &>/dev/null; then
    echo "→ Running mypy..."
    mypy app/ || FAILED=1
else
    echo "[SKIP] mypy not installed — run: pip install mypy"
fi

# ----------------------------------------------------------
# Result
# ----------------------------------------------------------
if [ "$FAILED" -ne 0 ]; then
    echo ""
    echo "===== Hermes: FAILED ====="
    exit 1
fi

echo ""
echo "===== Hermes: OK ====="
exit 0
