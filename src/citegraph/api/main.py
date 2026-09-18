from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from citegraph.api.routes import router
from citegraph.api.security import require_api_key, warn_if_unauthenticated
from citegraph.config import settings
from citegraph.logging_config import setup_logging

setup_logging()
warn_if_unauthenticated()

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
