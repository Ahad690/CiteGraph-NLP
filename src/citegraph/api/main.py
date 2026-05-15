from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from citegraph.api.routes import router
from citegraph.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="CiteGraph-NLP API",
    description="Backend API for Confidence-Aware Citation Lineage and Knowledge Graph System",
    version="0.1.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}
