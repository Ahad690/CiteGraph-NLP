---
commit: 5adceb1956292b39141487318ba788b1949e2a7e
short_sha: 5adceb19
author: Ahad Imran
date: 2026-05-23
message: "Fix order: clean .bak files before finding nginx config\n\nPrevious run found leadgen.bak first via grep, then cleanup deleted it,\nthen backup step failed because source no longer existed.\nNow: clean bak files → find active config → backup → modify.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
model: gpt-5-5-thinking
provider: chatgpt
thinking_effort: extended
reviewed_at: 2026-05-23T11:22:28.277Z
---

# Code Review: 5adceb19

> Fix order: clean .bak files before finding nginx config

## Summary

This commit fixes the ordering in the backend deployment workflow so stale Nginx backup files are removed before searching for the active config. Previously, `grep` could select a `.bak` file under `/etc/nginx/sites-enabled`, then the cleanup step deleted that file before the backup step, causing the deployment to fail. The new flow is correctly ordered: clean backup files, search for a non-`.bak` config, verify it still exists, then back it up and modify it (`.github/workflows/deploy-backend.yml:L105-L118`).

## Issues & Suggestions

- **Positive: cleanup now happens before discovery**  
  `.github/workflows/deploy-backend.yml:L107-L108` correctly removes stale `.bak.*` and `.bak.disabled` files before searching for the active Nginx config. This directly fixes the prior failure mode where the workflow selected a backup file and then deleted it.

- **Positive: config discovery excludes backups defensively**  
  `.github/workflows/deploy-backend.yml:L111` adds `grep -v '\.bak'`, which is a useful second layer of protection even after cleanup.

- **Positive: file existence check prevents backup of deleted/missing files**  
  `.github/workflows/deploy-backend.yml:L114` now requires both a non-empty `NGINX_CONF` and `-f "$NGINX_CONF"`, preventing the exact failure described in the commit message.

- **Cleanup is still silent and broad**  
  `.github/workflows/deploy-backend.yml:L108` deletes matching files without logging which files were removed. For deploy safety, prefer `find /etc/nginx/sites-enabled -maxdepth 1 \( -name '*.bak.*' -o -name '*.bak.disabled' \) -print -delete` so the logs show exactly what was cleaned.

- **Config discovery is still limited to `sites-enabled`**  
  `.github/workflows/deploy-backend.yml:L111` searches only `/etc/nginx/sites-enabled/`. If the active config later moves to `/etc/nginx/conf.d/`, the deployment will fail even though Nginx is valid. This may be fine for the current host, but document that assumption or include both paths.

- **Backup path is still not captured for rollback**  
  `.github/workflows/deploy-backend.yml:L117-L118` creates a backup in `/etc/nginx/backups`, but later validation failure cannot restore it unless the path is stored in a variable. This should be paired with rollback logic around `nginx -t`.

## Security & Performance

Security impact is low and positive: removing stale backup configs from an active Nginx include directory reduces accidental exposure or broken routes. Performance impact is negligible; these are deploy-time shell operations. Operational reliability improves, but rollback-on-failure and logged cleanup would make this safer.

## Overall Score: 9/10

This is a focused and correct fix for the immediate deployment failure. It improves ordering and adds defensive filtering. The remaining concerns are mostly operational hardening: log deletions, broaden or document config discovery, and add rollback.

## Recommendations

1. Log deleted backup files before removing them (`.github/workflows/deploy-backend.yml:L108`).  
2. Store the backup path in `BACKUP_PATH` and restore it if `nginx -t` fails (`.github/workflows/deploy-backend.yml:L117-L118`).  
3. Document that the active config must live in `/etc/nginx/sites-enabled/`, or search `/etc/nginx/conf.d/` too (`.github/workflows/deploy-backend.yml:L111`).  
4. Add a post-reload health check for `/citegraph/health`.