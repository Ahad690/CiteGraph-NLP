# Appendix B: Configuration Reference

All settings are read by `pydantic-settings` from environment variables or a
`.env` file.

## B.1 Application

| Setting | Variable | Default | Notes |
|---------|----------|---------|-------|
| `app_env` | `APP_ENV` | `development` | A non-development value without `API_KEY` logs a startup warning |
| `log_level` | `LOG_LEVEL` | `INFO` | |

## B.2 Security

| Setting | Variable | Default | Notes |
|---------|----------|---------|-------|
| `api_key` | `API_KEY` | unset | When set, every `/api` route requires `X-API-Key`. Unset in the deployment (§7.5) |
| `cors_origins` | `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed browser origins |

A wildcard CORS policy is deliberately not used. It would let any page a
developer visits drive their locally running instance and read the responses.

## B.3 Providers

| Setting | Variable | Default | Notes |
|---------|----------|---------|-------|
| `openalex_email` | `OPENALEX_EMAIL` | unset | Polite-pool identification; materially affects latency |
| `enable_openalex` | `ENABLE_OPENALEX` | `true` | Primary provider |
| `enable_crossref` | `ENABLE_CROSSREF` | `true` | Publisher-deposited metadata |
| `enable_europe_pmc` | `ENABLE_EUROPE_PMC` | `true` | **Required for abstract backfill** (§6.3) |
| `enable_pubmed` | `ENABLE_PUBMED` | `false` | Reserved; no provider implemented |
| `enable_semantic_scholar` | `ENABLE_SEMANTIC_SCHOLAR` | `false` | Reserved; no provider implemented |
| `enable_clinical_trials` | `ENABLE_CLINICAL_TRIALS` | `false` | Reserved; no provider implemented |
| `enable_unpaywall` | `ENABLE_UNPAYWALL` | `false` | Reserved; no provider implemented |

Disabling Europe PMC removes the abstract backfill and, on the basis of
Section 6.3, would leave roughly 28% of papers without extractable text.

## B.4 Traversal and weighting

| Setting | Variable | Default | Notes |
|---------|----------|---------|-------|
| `default_backward_depth` | `DEFAULT_BACKWARD_DEPTH` | `2` | Clamped 0–3 |
| `default_forward_depth` | `DEFAULT_FORWARD_DEPTH` | `1` | Clamped 0–2 |
| `default_max_total_papers` | `DEFAULT_MAX_TOTAL_PAPERS` | `100` | Clamped 1–200 |
| `weight_alpha` | `WEIGHT_ALPHA` | `0.75` | Weight on the population evidence term |
| `weight_beta` | `WEIGHT_BETA` | `0.25` | Weight on the journal term |
| `n_reference` | `N_REFERENCE` | `100000` | Reference population for log normalisation |

`max_total_papers` is exposed in the dashboard as a 10–200 slider. Section 6.6
recommends 100 or below: 200 takes around 3.5 minutes and exceeds NFR-1.

## B.5 Storage and optional services

| Setting | Variable | Default | Notes |
|---------|----------|---------|-------|
| `data_dir` | `DATA_DIR` | `./data` | |
| `sqlite_path` | `SQLITE_PATH` | `./data/cache/citegraph.sqlite` | Run persistence |
| `enable_grobid` | `ENABLE_GROBID` | `true` | **Flag only; GROBID is never called** (§7.4) |
| `grobid_url` | `GROBID_URL` | `http://localhost:8070` | Unused |
| `enable_neo4j` | `ENABLE_NEO4J` | `false` | **Flag only; no Neo4j integration is implemented** |
| `neo4j_uri` / `neo4j_user` | n/a | n/a | Unused |
| `neo4j_password` | `NEO4J_PASSWORD` | unset | No default; required before enabling the profile |

The GROBID and Neo4j flags are configuration remnants of capabilities specified
in the proposal but not built. They are listed here rather than removed so the
divergence in Section 7.4 is traceable from the configuration itself.

## B.6 Internal constants

Not environment-configurable; changing them requires a code edit.

| Constant | Value | Purpose |
|----------|-------|---------|
| `OpenAlexProvider.BATCH_SIZE` | 50 | Identifiers per batched metadata request |
| `OpenAlexProvider.MAX_FORWARD_CITATIONS` | 200 | Citing works retrieved per paper |
| `CitationTraversal.FORWARD_BUDGET_SHARE` | 0.35 | Budget reserved for forward traversal (§4.4.4) |
| `CitationTraversal.MAX_CONCURRENT_EXPANSIONS` | 5 | Concurrent reference/citation lookups |
| `CitationTraversal.TITLE_KEY_PREFIX` | 80 | Title prefix length for duplicate detection |
| `CitationTraversal.MIN_TITLE_KEY_LENGTH` | 25 | Shortest title eligible for prefix matching |
| `GraphAnalytics.MAX_PATHS_EXAMINED` | 50,000 | Safety cap on path enumeration (§6.6.4) |
