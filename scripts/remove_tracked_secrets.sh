#!/usr/bin/env bash
# Untrack sensitive files from git index without deleting local copies.
set -euo pipefail
FILES=(.env victron-secrets.env ha-discovery.env health.env user_settings.py)
for f in "${FILES[@]}"; do
  if git ls-files --error-unmatch "$f" > /dev/null 2>&1; then
    echo "Removing $f from git index"
    git rm --cached "$f" || true
  else
    echo "Not tracked: $f"
  fi
done

echo "Create a commit to record removal:"
echo "  git commit -m 'chore: stop tracking local secret files'"

echo "Consider running git-filter-repo or BFG to remove these files from history if they were pushed to a remote. See SECURITY_REMOVE_SECRETS.md"
