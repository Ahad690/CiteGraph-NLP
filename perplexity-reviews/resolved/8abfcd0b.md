---
commit: 8abfcd0b9b2e8b2558d48ad2099778d6121b8072
short_sha: 8abfcd0b
author: Ahad Imran
date: 2026-05-23
message: "Use existing hetzner-api.duckdns.org Caddy for HTTPS\n\nReuse the existing Caddy + DuckDNS HTTPS setup from Penora:\n- Backend deploy adds /citegraph handle_path route to existing Caddyfile\n- Frontend builds with VITE_API_BASE=https://hetzner-api.duckdns.org/citegraph\n- Caddy strips /citegraph prefix before forwarding to backend on port 8002\n- No new domain or secrets needed\n\nCo-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
model: gpt-5-5-thinking
provider: chatgpt
thinking_effort: extended
reviewed_at: 2026-05-22T23:01:34.301Z
---

# Code Review: 8abfcd0b

> Use existing hetzner-api.duckdns.org Caddy for HTTPS

## Summary

This commit switches the frontend and backend deployment to use an existing DuckDNS + Caddy HTTPS setup at `https://hetzner-api.duckdns.org/citegraph`, eliminating the need for new domain configuration or secrets. The backend deploy now appends a `/citegraph` `handle_path` route to the existing Caddyfile if it doesn’t already exist, forwarding requests to port 8002 (deploy-backend.yml:L107-L124). The frontend builds with `VITE_API_BASE=https://hetzner-api.duckdns.org/citegraph` (deploy-frontend.yml:L30). The prior standalone Caddyfile is removed, and all domain/env variable handling is simplified.

## Issues & Suggestions

- **Caddyfile Insertion via `sed` (deploy-backend.yml:L110-L118)**:  
  - Using `sed` to insert the `handle_path` block is brittle. If the site block formatting changes, it could fail silently. Consider using a templating approach or dedicated Caddy JSON API (`caddy adapt`) for more robust insertion.  
  - Verify that `/citegraph/*` correctly strips the prefix; `handle_path` behavior is sensitive to trailing slashes. Test requests like `GET /citegraph/health` to confirm proper forwarding.

- **Idempotency Check (deploy-backend.yml:L119-L121)**:  
  - Currently checks if `handle_path /citegraph` exists and skips. Fine for repeated deploys, but edge cases where the block is partially malformed may bypass detection. Logging or dry-run validation may improve reliability.

- **Hardcoded Frontend API Base (deploy-frontend.yml:L30)**:  
  - Using `https://hetzner-api.duckdns.org/citegraph` is simple, but loses flexibility if the backend ever moves. Consider keeping a secret or environment variable for CI/CD so future redeploys don’t require source changes.

- **Removal of Prior Caddyfile (deleted file mode, Caddyfile)**:  
  - Ensure the backend container or VM does not expect this file elsewhere in scripts. All references to `Caddyfile` in previous deploy steps should now refer to the live system copy.

- **No TLS/HTTPS Validation in Deploy Script**:  
  - The script assumes DuckDNS + Caddy automatically provides valid TLS. It would be safer to test the endpoint after reload with `curl -vk https://hetzner-api.duckdns.org/citegraph/health` to catch any certificate or proxy misconfigurations.

## Security & Performance

- **Security**: Using HTTPS removes mixed content issues; no new sensitive secrets are exposed.  
- **Performance**: `handle_path` introduces minimal overhead; reverse proxy is efficient for this traffic.  
- **Scalability**: This is suitable for the current scale. If traffic grows significantly, consider using a more robust reverse proxy or load balancer in front of Caddy.

## Overall Score: 9/10

This is a clean simplification of the HTTPS deployment and eliminates unnecessary domain/secrets setup. Minor brittleness in `sed` insertion and hardcoded frontend base prevent a perfect score, but the solution is practical and low-risk for the current project scale.

## Recommendations

1. **Add Post-Deploy Health Check**: Verify that `https://hetzner-api.duckdns.org/citegraph/health` returns 200 after Caddy reload (deploy-backend.yml:L124).  
2. **Consider Using Caddy JSON API or Templates**: Avoid `sed` for route insertion (deploy-backend.yml:L110-L118) to make future changes more robust.  
3. **Parameterize Frontend API Base**: Store `VITE_API_BASE` in a CI/CD secret instead of hardcoding (deploy-frontend.yml:L30) for flexibility.  
4. **Test Edge Cases for Prefix Stripping**: Confirm that `/citegraph/` requests and subpaths properly map to backend routes without double slashes.  
5. **Monitor Logs**: Ensure Caddy reloads do not fail silently and that the route is active.  

These steps will improve maintainability and prevent deployment failures in future iterations.