#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_FILE="$ROOT_DIR/molecule/default/tests/test_inventory_from_nothing.py"

GREEN='\033[32m'; RED='\033[31m'; CYAN='\033[36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

echo ""
echo -e "  ${CYAN}${BOLD}=============================================="
echo -e "  ARIA — Automated Review & Intelligence Analyst"
echo -e "  Mission 1.6: Inventory from Nothing"
echo -e "  ==============================================${RESET}"

cd "$ROOT_DIR"
if [ -f "$ROOT_DIR/venv/bin/activate" ]; then
    source "$ROOT_DIR/venv/bin/activate"
fi

ARIA_COLOR=1 python3 -m pytest "$TEST_FILE" --tb=no --no-header -q 2>&1 1>/dev/null \
    | grep -vE '^(assert |FAILED| *\+  where|  *\+  |[0-9]+ (passed|failed))' || true
EXIT_CODE=${PIPESTATUS[0]}

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}=============================================="
    echo -e "  ARIA: All objectives verified."
    echo -e "  Mission 1.6 status: COMPLETE"
    echo -e ""
    echo -e "  From one line — a subnet — you mapped the whole"
    echo -e "  fleet, and your inventory survives Nyx's rotation."
    echo -e "  That is day-zero cartography. Well done, Sub-Lieutenant."
    echo -e "  ==============================================${RESET}"
else
    echo -e "  ${RED}${BOLD}=============================================="
    echo -e "  ARIA: Deficiencies detected."
    echo -e "  Review the findings above and correct."
    echo -e "  Run 'make test' again when ready."
    echo -e "  ==============================================${RESET}"
fi

echo ""
exit $EXIT_CODE
