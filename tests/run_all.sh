#!/usr/bin/env bash
# tests/run_all.sh — Run every scenario_*.sh test and report results.
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

passed=0
failed=0
errors=()

for scenario in "$TESTS_DIR"/scenario_*.sh; do
    name="$(basename "$scenario" .sh)"
    echo ""
    echo "========================================"
    echo "Running: $name"
    echo "========================================"

    if bash "$scenario"; then
        echo -e "\033[0;32mPASSED\033[0m: $name"
        passed=$((passed + 1))
    else
        echo -e "\033[0;31mFAILED\033[0m: $name"
        failed=$((failed + 1))
        errors+=("$name")
    fi
done

echo ""
echo "========================================"
echo "Results: ${passed} passed, ${failed} failed"
if [[ ${#errors[@]} -gt 0 ]]; then
    echo "Failed scenarios:"
    for e in "${errors[@]}"; do
        echo "  - $e"
    done
fi
echo "========================================"

exit "$failed"
