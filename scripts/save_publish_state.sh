#!/usr/bin/env bash
# Persist results after publishing. State-save errors are fatal.
set -euo pipefail

state_path="${1:-out/daily/plan.json}"
message="${2:-chore: record publish links $(date -u +%F)}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add -- "$state_path"
if [[ "${PUBLISH_OUTCOME:-failure}" == "success" ]]; then
  rm -f out/daily/publish_pending.json
  git add -- out/daily/publish_pending.json
fi
if ! git diff --cached --quiet; then
  git commit -m "$message"
fi
git pull --rebase -q
git push -q
