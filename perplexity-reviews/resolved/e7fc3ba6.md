---
commit: e7fc3ba62fc0277ac6a7ba15ca96218eee49050b
short_sha: e7fc3ba6
author: Ahad Imran
date: 2026-05-23
message: "Fix: add /citegraph route to Nginx (not Caddy)\n\nServer uses Nginx for HTTPS reverse proxy, not Caddy.\nFinds the Nginx config for hetzner-api.duckdns.org and injects\na location /citegraph/ block that proxies to localhost:8002.\n\nCo-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
model: gpt-5-5-thinking
provider: chatgpt
thinking_effort: extended
reviewed_at: 2026-05-22T23:13:02.138Z
---

# Code Review: e7fc3ba6

> Fix: add /citegraph route to Nginx (not Caddy)

## Summary

This commit replaces the previous Caddy-focused route injection with an Nginx-specific solution (deploy-backend.yml:L105-L117). The workflow now searches for the Nginx config containing `hetzner-api.duckdns.org` under `/etc/nginx/sites-enabled/` or `/etc/nginx/conf.d/`, and if the `/citegraph` location block is missing, it inserts it before the last closing brace using `awk`, then validates and reloads Nginx. It logs whether the block was added, already present, or no config was found.

## Issues & Suggestions

- **Insertion Accuracy** (deploy-backend.yml:L109-L115):  
  - The current `awk` logic inserts the `/citegraph` block before the first line that matches a closing brace (`}`) not preceded by a previous `location /citegraph/`. This may fail or insert in the wrong context if the config has multiple server blocks, nested braces, or includes. Consider restricting insertion to the `server` block that contains `server_name hetzner-api.duckdns.org;`.  
  - Multi-line blocks in `awk` can be fragile. If the Nginx config format changes (tabs, spaces, comments), the block may be misplaced.

- **Idempotency**:  
  - The check `! grep -q citegraph` could fail if `citegraph` exists in a comment or variable elsewhere. Use `grep -q 'location /citegraph/'` for more precision.

- **Validation**:  
  - `nginx -t` is used, which is good, but the script continues to overwrite the config even if `nginx -t` fails. Consider testing first, then moving the temporary file to avoid breaking Nginx on syntax errors.

- **Backup**:  
  - Overwriting `$NGINX_CONF` without backup is risky. A backup (e.g., `$NGINX_CONF.bak`) before modification is recommended.

- **Error Handling / Logging**:  
  - The current logging only prints to stdout. Failures in `awk` or `nginx -t` could go unnoticed in CI logs. Consider capturing stderr and exit codes.

- **Shell Safety**:  
  - The embedded awk script uses `$host`, `$remote_addr`, `$proxy_add_x_forwarded_for`, `$scheme`. These will be interpreted by Nginx at runtime, but ensure no shell expansion happens (current quoting seems fine, but double-check CI behavior).

## Security & Performance

- **Security**: Minimal risk; only local config files and internal proxy are modified. Ensure file permissions remain strict.  
- **Performance**: Negligible impact; Nginx reload is lightweight.  
- **Scalability**: Suitable for single server. Multi-server or multi-domain environments would need a more declarative approach (e.g., separate include files).

## Overall Score: 8.5/10

The commit fixes the previous Caddy assumption and correctly implements an Nginx route. Score is limited by potential fragility with multiple server blocks, lack of backup, and idempotency issues.

## Recommendations

1. **Restrict insertion to the correct `server` block**: Match `server_name hetzner-api.duckdns.org;` rather than any closing brace (deploy-backend.yml:L109).  
2. **Use a backup**: Copy `$NGINX_CONF` to `$NGINX_CONF.bak` before overwriting.  
3. **Validate before overwriting**: Run `nginx -t -c /tmp/nginx_citegraph.conf` first. Only move if test passes.  
4. **Improve idempotency**: Check specifically for `location /citegraph/` instead of `citegraph`.  
5. **Optional**: Consider moving the block insertion logic into a small shell script or Ansible playbook for clarity and maintainability.  

These steps will ensure safer deployment and reduce the risk of misconfigurations in production.