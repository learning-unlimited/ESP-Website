#!/usr/bin/env bash
# check_csrf_exempt.sh — CI check that flags new uses of @csrf_exempt.
#
# Allowed usages (add justifications here as comments):
#   - esp/formstack/views.py:formstack_webhook  — External webhook; verified via handshake key
#   - esp/program/views.py:submit_transaction    — Cybersource payment postback
#   - esp/users/views/__init__.py:unsubscribe_oneclick — RFC 8058 List-Unsubscribe-Post
#
# Usage:
#   ./scripts/check_csrf_exempt.sh
#   Exit code 0 = only known usages found.
#   Exit code 1 = new/unknown csrf_exempt usage detected.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Known allowed files (relative to repo root)
ALLOWED_FILES=(
    "esp/esp/formstack/views.py"
    "esp/esp/program/views.py"
    "esp/esp/users/views/__init__.py"
)

# Find all Python files using @csrf_exempt (excluding tests and migrations)
# Use while-read loop to handle paths with spaces
EXIT_CODE=0

while IFS= read -r file; do
    [ -z "$file" ] && continue
    rel_path="${file#"$REPO_ROOT"/}"
    is_allowed=false
    for allowed in "${ALLOWED_FILES[@]}"; do
        if [[ "$rel_path" == "$allowed" ]]; then
            is_allowed=true
            break
        fi
    done
    if [[ "$is_allowed" == "false" ]]; then
        echo "❌ NEW @csrf_exempt usage found in: $rel_path"
        grep -n "@csrf_exempt" "$file"
        EXIT_CODE=1
    fi
done < <(grep -rl "@csrf_exempt" "$REPO_ROOT/esp/esp/" \
    --include="*.py" \
    | grep -v "test" \
    | grep -v "migration" \
    | sort -u || true)

if [[ "$EXIT_CODE" == "0" ]]; then
    echo "✅ No unexpected @csrf_exempt usages found."
fi

exit $EXIT_CODE
