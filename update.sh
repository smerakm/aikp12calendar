#!/bin/bash
# Regenerates index.html from the ICS feeds, commits it, and pushes.
set -euo pipefail
cd "$(dirname "$0")"

python3 generate.py

# Ignore the "Generated <timestamp> from ..." line when deciding whether
# anything meaningful changed, so a re-run with no schedule changes doesn't
# produce a commit for just the timestamp.
strip_generated_line() {
    grep -v '^\s*<div class="sub">Generated ' "$@"
}

if diff -q <(strip_generated_line index.html) <(git show HEAD:index.html 2>/dev/null | strip_generated_line) >/dev/null 2>&1; then
    echo "No meaningful changes to index.html, nothing to commit."
    exit 0
fi

git add index.html
git commit -m "update $(date +%Y-%m-%d)"
git push
