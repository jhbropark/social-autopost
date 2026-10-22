#!/usr/bin/env bash
# Persist publish state only after external publishing has completed.
# Fail closed: a failed rebase or push must fail the workflow so operators can
# reconcile state before any later run can publish again.
set -euo pipefail

state_path="${1:-out/daily/plan.json}"
message="${2:-chore: record publish links $(date -u +%F)}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add -- "$state_path"
if ! git diff --cached --quiet -- "$state_path"; then
  git commit -m "$message"
fi
git pull --rebase -q
git push -q
