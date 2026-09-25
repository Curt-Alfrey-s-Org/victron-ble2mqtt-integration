# Remove secrets from git (operator checklist)

This repository must not track credentials, API tokens, or TLS private keys.

## Immediate actions if secrets were committed

1. **Rotate** every credential that may have been exposed (MQTT passwords, HA long-lived tokens, GHCR tokens, TLS keys used by reverse proxies, ADVKEY material if ever committed).
2. Store replacements outside git (host `.env` / `victron-secrets.env` with mode `600`, or a secrets manager). Prefer `victron-secrets.env` for ADVKEY_* only.
3. Confirm `.gitignore` covers local secret paths (see repo root `.gitignore`: `.env`, `*.env`, `ssl/*.key`, `ssl/*.crt`, swarm env files).
4. **Stop tracking** any file that slipped in:

   ```bash
   git rm --cached --ignore-unmatch .env victron-secrets.env ha-discovery.env health.env ssl/tools.key ssl/tools.crt
   git commit -m "chore: stop tracking local secrets and TLS keys"
   ```

5. **Purge history** if the secret was pushed (required for private keys and passwords):

   - Preferred: [git-filter-repo](https://github.com/newren/git-filter-repo)

     ```bash
     git clone --mirror <repo-url> repo.git
     cd repo.git
     git filter-repo --invert-paths \
       --paths .env \
       --paths victron-secrets.env \
       --paths ha-discovery.env \
       --paths health.env \
       --paths user_settings.py \
       --paths ssl/tools.key \
       --paths ssl/tools.crt
     git push --force --all
     git push --force --tags
     ```

   - Alternative: BFG Repo-Cleaner

6. After a history rewrite, **rotate again** (assume prior values leaked).
7. Keep pre-commit / secret scanning enabled so this does not recur.

## 2026-07 cleanup note

`ssl/tools.key` and `ssl/tools.crt` were removed from the working tree and from the git index. They remain in **older commits** until history is purged (step 5). Treat that keypair as compromised: generate a new cert on the host (see `ssl/README.md`) and do not re-add keys to the repo.

## 2026-09 cleanup note

`nginx/.htpasswd` (basic-auth hashes for the retired tools reverse proxy) and
`swarm/auto-discovery.env` were removed from the git index (both were already
listed in `.gitignore`). They remain in **older commits** until history is
purged (step 5).

- Treat every username/password that was ever in `nginx/.htpasswd` as exposed:
  the hashes can be brute-forced offline. Change that password anywhere it is
  reused. nginx was removed from `docker-compose.tools.yml`, so the file is no
  longer needed; regenerate it locally with `htpasswd -c nginx/.htpasswd <user>`
  only if you bring the proxy back.
- `swarm/auto-discovery.env` is meant to hold non-secret discovery settings; a
  placeholder template now lives at `swarm/auto-discovery.env.example`. If you
  ever put MQTT credentials in it, rotate them.
- **Before `git pull` on a host**, copy both files aside: pulling a commit that
  stops tracking a file deletes the working-tree copy. Restore them afterwards;
  they are ignored from now on.

## Related

- `DEPLOY.md` — `.env` / `victron-secrets.env` layout
- `ssl/README.md` — local TLS generation
- `docs/ENGINEERING_STANDARDS_PLAN.md` — Phase 5 threat model
