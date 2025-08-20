This repository contains sensitive files that should not be committed to git.

Follow these steps to remove secrets from the working tree safely and stop tracking them:

1) Rotate credentials immediately for any secrets that were exposed (MQTT passwords, API tokens, GHCR tokens, etc.).

2) Add secrets to a secure store (GitHub Secrets, HashiCorp Vault, Docker secrets) and do not keep them in the repo.

3) Update `.gitignore` so the sensitive files are not tracked (the repo includes a change to `.gitignore`).

4) Stop tracking the files with git (this un-stages them but keeps the files locally):

   git rm --cached .env victron-secrets.env ha-discovery.env health.env user_settings.py || true
   git commit -m "chore: stop tracking local env/secret files"

5) Purge secrets from git history (optional, required if you pushed secrets to a remote):

   - Recommended: use `git filter-repo` (fast and maintained)
     * Install: `pip install git-filter-repo`
     * Run (from a fresh clone):

       git clone --mirror <repo-url> repo.git
       cd repo.git
       git filter-repo --invert-paths --paths .env --paths victron-secrets.env --paths ha-discovery.env --paths health.env --paths user_settings.py
       git push --force --all
       git push --force --tags

   - Alternative: BFG Repo-Cleaner

6) After purging, inform any providers and rotate secrets again because they may have been leaked.

7) Add secret-scanning and pre-commit hooks to avoid accidental commits in the future.

If you'd like I can run the untracking git commands and prepare a branch/PR that removes tracked secrets; tell me to proceed and which files to untrack if you want a narrower set.
