# Local setup guide

Step-by-step instructions to run CiteGraph-NLP on your machine, from a fresh
clone to a working dashboard.

Nothing in this repository is shared infrastructure. The scholarly APIs the
system reads from are public and free, and the database is a local SQLite
file, so there are no credentials you need from anyone. The only thing worth
configuring is an email address for OpenAlex, explained in step 4.

**Time:** about ten minutes, most of it waiting for `pip install`.

---

## What you need first

| Requirement | Version | Check with |
|-------------|---------|------------|
| Python | 3.10 or newer | `python --version` |
| Node.js | 18 or newer, for the dashboard | `node --version` |
| Git | any recent | `git --version` |

Docker is optional. You need it only for GROBID (PDF parsing) or Neo4j,
neither of which the default pipeline uses.

---

## 1. Clone and create a virtual environment

```bash
git clone https://github.com/Ahad690/CiteGraph-NLP.git
cd CiteGraph-NLP
python -m venv .venv
```

Activate it. This is the step people skip, and then `pip install` writes into
the system Python:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows Git Bash
source .venv/Scripts/activate
```

Your prompt should now start with `(.venv)`.

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

The second line installs the project itself. Skip it and `import citegraph`
fails, because the package lives under `src/` and nothing puts that on the
path for you.

There is no spaCy model to download. Extraction only needs sentence
boundaries, and spaCy's rule-based splitter ships with spaCy itself.

Both steps at once:

```bash
make install
```

---

## 3. Create your environment file

```bash
cp .env.example .env
```

The defaults work as-is. You can start the server now and it will run.

---

## 4. Settings worth changing

All settings are read from `.env` by Pydantic. The full list is in
[the configuration reference](../README.md#configuration-reference) and in
Appendix B of the thesis; these four are the ones that matter on a first run.

### `OPENALEX_EMAIL` — recommended

```ini
OPENALEX_EMAIL=you@example.com
```

OpenAlex serves anonymous traffic from a shared pool that is slower and more
aggressively rate-limited. Supplying an email puts you in the polite pool.
It is not a key, nothing is sent to you, and it measurably speeds up
traversals.

### `API_KEY` — leave unset locally

```ini
# API_KEY=some-long-random-string
```

Unset, the API is open. That is correct for a local demo, and wrong for
anything reachable from the internet. Set it before deploying and the server
will require a matching `X-API-Key` header on every `/api` route. The server
logs a warning at startup whenever it is unset, so you will notice.

### `CORS_ORIGINS` — only if you change the frontend port

```ini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

The browser blocks the dashboard from calling the API unless the dashboard's
origin is listed here. If the dashboard loads but every request fails with a
CORS error in the console, this is why.

### `DEFAULT_MAX_TOTAL_PAPERS` — lower it while testing

```ini
DEFAULT_MAX_TOTAL_PAPERS=100
```

A 100-paper run takes a minute or two. Drop it to 25 while you are checking
that everything works, then put it back.

---

## 5. Start the backend

```bash
uvicorn citegraph.api.main:app --reload
```

| URL | What it is |
|-----|------------|
| `http://localhost:8000/health` | should return `{"status":"ok"}` |
| `http://localhost:8000/docs` | interactive API docs, generated from the code |

Leave this terminal running.

---

## 6. Start the dashboard

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 7. Check it works end to end

Paste a DOI into the dashboard, or drive the API directly:

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"query_type":"doi","value":"10.1056/NEJMoa2001017"}'
```

That returns a `run_id`. Poll it:

```bash
curl http://localhost:8000/api/runs/<run_id>
```

`status` moves `started` to `running` to `completed`. A 100-paper traversal
takes roughly one to two minutes; most of that is waiting on the scholarly
APIs, not computation.

---

## Optional services

Neither is needed for the default pipeline.

```bash
# GROBID, for parsing uploaded PDFs
docker compose up -d grobid

# Neo4j, as an alternative to the in-memory NetworkX graph
docker compose --profile neo4j up -d neo4j
```

Neo4j has no default password in this repository, deliberately: a shipped
default becomes the real password the first time somebody enables the profile
without thinking. Set `NEO4J_PASSWORD` before starting it.

---

## Running the tests

```bash
pytest -q
```

152 tests. If they pass, your install is sound.

---

## When something is wrong

**`ModuleNotFoundError: citegraph`** — `pip install -e .` was skipped, or the
virtual environment is not active. Check with `pip show citegraph-nlp`.

**Dashboard loads, every request fails** — open the browser console. A CORS
error means `CORS_ORIGINS` does not list the dashboard's origin. A connection
refused means the backend is not running.

**Runs finish with few nodes** — check the `warnings` array in the result. A
provider outage degrades a run rather than failing it, so a thin graph is
reported there rather than as an error.

**Runs are slow** — set `OPENALEX_EMAIL`. Anonymous OpenAlex traffic is
throttled.

---

## Related documentation

- [API reference](API.md) — every endpoint in detail
- [Deployment](DEPLOYMENT.md) — running this on a server
- [User guide](../USER_GUIDE.md) — using the dashboard
- [Project report](../PROJECT_REPORT.md) — what the system does and why
