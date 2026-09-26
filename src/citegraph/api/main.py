from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from citegraph.api.routes import router
from citegraph.api.security import require_api_key, warn_if_unauthenticated
from citegraph.config import settings
from citegraph.logging_config import setup_logging

setup_logging()
warn_if_unauthenticated()
# Collects every configuration fault and refuses once, rather than letting the app
# come up open and being fixed one restart at a time. Refusal is production-only:
# a local demo with no API key is a supported way to run this.
settings.refuse_if_misconfigured()

app = FastAPI(
    title="CiteGraph-NLP API",
    description="Backend API for Confidence-Aware Citation Lineage and Knowledge Graph System",
    version="0.1.0"
)

# CORS is restricted to the configured frontend origins. A wildcard would let
# any page a developer visits drive their locally-running instance and read the
# JSON back. Set CORS_ORIGINS to the deployed frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(router, prefix="/api", dependencies=[Depends(require_api_key)])

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    """Which build is answering.

    Unauthenticated, beside /health, because its whole purpose is to let something
    outside the box ask. On 2026-09-19 this deployment was verified by HTTP by
    hand; before that, deploy-backend.yml carried 46.225.8.77 as a fallback after
    that box was deleted, and nothing tied the running container to the commit
    that had been pushed. A hand-uploaded bundle once sat behind a live domain
    through three green CI runs in Terminux, which is the incident this answers.

    GIT_SHA and BUILD_TIME are passed to `docker run` by the deploy workflow, so
    no Dockerfile change is needed. Both are absent when the app is started by
    hand, and the reply says so rather than inventing a value:
    scripts/check_deployed_build.py refuses an unstamped build.
    """
    return {
        "service": "citegraph-api",
        "version": app.version,
        "git_sha": settings.git_sha,
        "built_at": settings.build_time,
    }

