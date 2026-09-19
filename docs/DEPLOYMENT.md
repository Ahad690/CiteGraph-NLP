# Deployment

How the live system is deployed, what it runs on, and what to do when a
deploy fails.

Both halves deploy from GitHub Actions on a push to `main`. Neither is
deployed by hand.

| Half | Where | URL |
|------|-------|-----|
| Frontend | Cloudflare Pages | <https://citegraph-nlp.pages.dev> |
| Backend | Hetzner VPS, Docker behind nginx | <https://citegraph-api.penora.us> |

Verify both are up:

```bash
curl -s https://citegraph-api.penora.us/health     # {"status":"ok"}
curl -sI https://citegraph-nlp.pages.dev | head -1 # HTTP/2 200
```

---

## Backend

`.github/workflows/deploy-backend.yml`. Triggers on a push to `main` that
touches `src/**`, `requirements.txt`, `Dockerfile`, `.dockerignore` or the
workflow itself, and on manual dispatch.

### What the box looks like

The VPS is shared with four other projects, so the important constraint is
that CiteGraph must not disturb them.

| | |
|---|---|
| Host | `penora-prod-2`, 167.233.240.132 |
| Container | `citegraph-api` |
| Bind | **127.0.0.1:18030**, loopback only |
| Code | `/opt/citegraph-nlp/backend` |
| Data | `/opt/citegraph-nlp/data` |
| Env file | `/opt/citegraph-nlp/.env` |
| TLS | nginx + certbot, terminating for `citegraph-api.penora.us` |

Port 18030 rather than 18020 because terminux already holds 18020. Every app
on this box binds to loopback and is reached only through nginx; nothing
publishes to `0.0.0.0`. A container that published its port directly would
expose the API regardless of what nginx is configured to allow.

### Secrets and variables

Set in the repository's Actions settings.

| Name | Kind | Purpose |
|------|------|---------|
| `HETZNER_HOST` | secret | target IP. The workflow falls back to 167.233.240.132 if unset, so the host can be repointed without a code change |
| `HETZNER_SSH_KEY` | secret | private key for `root@` on the box |

### Deploying

Push to `main`, or run the workflow manually from the Actions tab. It builds
the image on the box, stops the old container and starts the new one under the
same name.

### When it fails

**SSH times out** — check `HETZNER_HOST` points at a live box. This project
previously pointed at 46.225.8.77, which was deleted on 2026-05-31; a workflow
that still names a dead IP hangs rather than erroring clearly.

**Container starts then exits** — read the logs on the box:

```bash
ssh root@167.233.240.132 'docker logs --tail 80 citegraph-api'
```

Most often a missing value in `/opt/citegraph-nlp/.env`. That file is not in
git and is not rewritten by the deploy, so a new required setting has to be
added there by hand before the deploy that needs it.

**502 from nginx** — the container is down or not listening on 18030:

```bash
ssh root@167.233.240.132 'docker ps --filter name=citegraph-api; ss -ltnp | grep 18030'
```

**Never run `docker compose up` in another project's directory on this box.**
At least one compose file there binds `0.0.0.0:8000` and would publicly expose
an API that is deliberately loopback-only.

---

## Frontend

`.github/workflows/deploy-frontend.yml`, deploying to Cloudflare Pages with
`wrangler-action`.

### Secrets and variables

| Name | Kind | Purpose |
|------|------|---------|
| `CLOUDFLARE_API_TOKEN` | secret | token with Pages edit permission |
| `CLOUDFLARE_ACCOUNT_ID` | secret | the account to deploy into |
| `VITE_API_BASE` | variable | API origin baked into the bundle; defaults to `https://citegraph-api.penora.us` |

### The API base is compiled in, not read at runtime

Vite substitutes `VITE_API_BASE` at build time. A wrong value produces a
bundle that calls the wrong host, and no amount of restarting fixes it — the
fix is always a rebuild.

Because that failure is invisible until a user clicks something, the workflow
greps the built assets for the expected origin and fails the build when it is
absent:

```bash
if ! grep -rqF "$api_base" dist/client/assets; then
  echo "ERROR: $api_base was not baked into the bundle."
  exit 1
fi
```

If you change `VITE_API_BASE`, re-run the frontend workflow. Changing it
without a rebuild changes nothing.

### CORS

The backend only answers browsers whose origin is listed in `CORS_ORIGINS` in
`/opt/citegraph-nlp/.env`. A new frontend origin needs adding there and the
container restarting, or every request from the new origin fails in the
browser while working fine from `curl`.

---

## Local container

To run the backend in Docker without touching the server:

```bash
docker compose up -d
curl http://localhost:8000/health
```

`docker-compose.yml` in this repository is the local development setup. The
production container is built and run by the workflow, not from this file.

---

## Rolling back

There is no blue/green slot for this service; a deploy replaces the running
container. To roll back, revert the commit and let the workflow redeploy:

```bash
git revert <bad-commit>
git push
```

That is slower than swapping an image tag but it keeps the box and the
repository describing the same thing, which matters more on a machine shared
with four other projects.

---

## Related documentation

- [Local setup](SETUP.md) — running it on your machine instead
- [API reference](API.md) — what the deployed service exposes
- [GitHub Actions setup notes](github-actions-deployment-setup.md) — the
  earlier Firebase Hosting pattern, kept because it documents the workflow
  structure this one grew from. The frontend has since moved to Cloudflare
  Pages, so treat the Firebase steps there as history rather than instructions.
