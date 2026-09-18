from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from datetime import datetime
import uuid
import logging
import json
import asyncio

from citegraph.models.paper import PaperQuery
from citegraph.models.run import RunResult
from citegraph.pipeline.orchestrator import PipelineOrchestrator
from citegraph.utils.tasks import task_manager

router = APIRouter()
orchestrator = PipelineOrchestrator()
logger = logging.getLogger(__name__)

# Persistent storage
from citegraph.storage.sqlite import SQLiteStore
store = SQLiteStore()

class RunRequest(PaperQuery):
    backward_depth: int = 2
    forward_depth: int = 1
    max_total_papers: int = 100
    use_pdf_parsing: bool = True

class RunStatus(BaseModel):
    run_id: str
    status: Literal["started", "running", "completed", "failed"]
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

@router.on_event("startup")
async def startup_event():
    await store.connect()

@router.on_event("shutdown")
async def shutdown_event():
    await task_manager.shutdown(timeout=15.0)
    await store.close()

@router.post("/runs", response_model=Dict[str, str])
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    # Enforce limits
    request.backward_depth = min(max(request.backward_depth, 0), 3)
    request.forward_depth = min(max(request.forward_depth, 0), 2)
    request.max_total_papers = min(max(request.max_total_papers, 1), 200)

    # Ensure DB is ready (failsafe)
    await store.connect()

    run_id = str(uuid.uuid4())
    try:
        await store.create_run(run_id)
    except Exception as e:
        logger.error(f"Failed to create run in DB: {e}")
        raise HTTPException(status_code=500, detail="Database error during run initialization")
    
    task = asyncio.create_task(execute_run(run_id, request))
    task_manager.register(task)
    
    return {"run_id": run_id, "status": "started"}

async def execute_run(run_id: str, request: RunRequest):
    try:
        await store.update_status(run_id, "running")
        query = PaperQuery(
            query_type=request.query_type,
            value=request.value,
            pdf_path=request.pdf_path
        )
        result = await orchestrator.run(
            query=query,
            backward_depth=request.backward_depth,
            forward_depth=request.forward_depth,
            max_papers=request.max_total_papers,
            run_id=run_id # Passing run_id for consistency
        )
        await store.save_result(run_id, result)
    except (RuntimeError, asyncio.CancelledError) as re:
        # DB closed or server shutting down
        logger.warning(f"Run {run_id} aborted during shutdown: {re}")
        # Try one last-ditch status update if connection still valid
        try:
            await store.update_status(run_id, "failed", "Aborted due to server shutdown")
        except:
            pass 
    except ValueError as e:
        # Input/resolution problems are the caller's own doing and are safe to
        # echo back -- they describe the query, not the server.
        logger.error(f"Run {run_id} failed: {e}")
        await store.update_status(run_id, "failed", str(e))
    except Exception as e:
        # Anything else may carry internal detail (filesystem paths, driver
        # messages), so keep it in the log and hand the caller a reference only.
        logger.exception(f"Run {run_id} failed: {e}")
        await store.update_status(
            run_id, "failed", f"Run failed due to an internal error (ref: {run_id})"
        )

@router.get("/runs/{run_id}", response_model=RunResult | RunStatus)
async def get_run(run_id: str):
    data = await store.get_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if data["status"] == "completed" and data["result_json"]:
        return RunResult.model_validate_json(data["result_json"])
    
    return RunStatus(
        run_id=data["run_id"],
        status=data["status"],
        error=data["error"],
        created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
    )

@router.get("/runs/{run_id}/graph")
async def get_graph(run_id: str):
    data = await store.get_run(run_id)
    if not data or not data.get("result_json"):
        raise HTTPException(status_code=404, detail="Run not found or not completed")
    
    result = RunResult.model_validate_json(data["result_json"])
    nodes = []
    for paper in result.papers:
        nodes.append({
            "id": paper.paper_id,
            "label": paper.title,
            "year": paper.year,
            "n_eff": next((r.n_eff for r in result.population_resolutions if r.paper_id == paper.paper_id), None)
        })
        
    edges = []
    for edge in result.citation_edges:
        edges.append({
            "source": edge.source_paper_id,
            "target": edge.target_paper_id,
            "weight": edge.final_weight
        })
        
    return {"nodes": nodes, "links": edges}

@router.get("/runs/{run_id}/export/json")
async def export_json(run_id: str):
    data = await store.get_run(run_id)
    if not data or not data.get("result_json"):
        raise HTTPException(status_code=404, detail="Run not found or not completed")
    return json.loads(data["result_json"])

@router.get("/runs/{run_id}/export/csv")
async def export_csv(run_id: str):
    data = await store.get_run(run_id)
    if not data or not data.get("result_json"):
        raise HTTPException(status_code=404, detail="Run not found or not completed")
    
    result = RunResult.model_validate_json(data["result_json"])
    # Simplified CSV for papers
    csv_lines = ["paper_id,title,year,journal,n_eff"]
    for paper in result.papers:
        n_eff = next((r.n_eff for r in result.population_resolutions if r.paper_id == paper.paper_id), "")
        title = paper.title.replace('"', '""')
        csv_lines.append(f'"{paper.paper_id}","{title}",{paper.year or ""},"{paper.journal or ""}",{n_eff}')
    
    return {"csv": "\n".join(csv_lines)}

@router.get("/runs/{run_id}/export/markdown")
async def export_markdown(run_id: str):
    data = await store.get_run(run_id)
    if not data or not data.get("result_json"):
        raise HTTPException(status_code=404, detail="Run not found or not completed")
    
    result = RunResult.model_validate_json(data["result_json"])
    generated_at_raw = data.get("updated_at")
    try:
        dt = datetime.fromisoformat(generated_at_raw.replace('Z', '+00:00'))
        generated_at = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        generated_at = generated_at_raw

    lines = [f"# CiteGraph-NLP Analysis Report", ""]
    lines.append(f"**Run ID**: `{run_id}`")
    lines.append(f"**Seed Paper ID**: `{result.seed_paper_id}`")
    lines.append(f"**Generated At**: {generated_at}")
    lines.append("")
    
    lines.append("## Probable Foundational Papers")
    lines.append("| Rank | Title | Year | Score | Explanation |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, p in enumerate(result.ranked_foundational_papers):
        lines.append(f"| {i+1} | {p['title']} | {p['year']} | {p['score']:.2f} | {p['explanation']} |")
    
    lines.append("")
    lines.append("## Population Evidence")
    lines.append("| Paper ID | N_eff | Status | Confidence |")
    lines.append("| --- | --- | --- | --- |")
    for res in result.population_resolutions:
        lines.append(f"| {res.paper_id} | {res.n_eff} | {res.status} | {res.confidence:.2f} |")
        
    return {"report": "\n".join(lines)}
