from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Literal, Optional
import uuid
import logging

from citegraph.models.paper import PaperQuery
from citegraph.models.run import RunResult
from citegraph.pipeline.orchestrator import PipelineOrchestrator

router = APIRouter()
orchestrator = PipelineOrchestrator()
logger = logging.getLogger(__name__)

# Store results in memory for MVP (could be SQLite/Redis later)
results_cache: Dict[str, RunResult] = {}

class RunRequest(PaperQuery):
    backward_depth: int = 2
    forward_depth: int = 1
    max_total_papers: int = 100
    use_pdf_parsing: bool = True

class RunStatus(BaseModel):
    run_id: str
    status: Literal["started", "running", "completed", "failed"]
    error: Optional[str] = None

# Store results and status
results_cache: Dict[str, RunResult] = {}
status_cache: Dict[str, RunStatus] = {}

@router.post("/runs", response_model=Dict[str, str])
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    status_cache[run_id] = RunStatus(run_id=run_id, status="started")
    
    background_tasks.add_task(execute_run, run_id, request)
    
    return {"run_id": run_id, "status": "started"}

async def execute_run(run_id: str, request: RunRequest):
    try:
        status_cache[run_id].status = "running"
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
            run_id=run_id
        )
        results_cache[run_id] = result
        status_cache[run_id].status = "completed"
    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")
        status_cache[run_id].status = "failed"
        status_cache[run_id].error = str(e)

@router.get("/runs/{run_id}", response_model=RunResult | RunStatus)
async def get_run(run_id: str):
    if run_id in results_cache:
        return results_cache[run_id]
    if run_id in status_cache:
        return status_cache[run_id]
    raise HTTPException(status_code=404, detail="Run not found")

@router.get("/runs/{run_id}/graph")
async def get_graph(run_id: str):
    if run_id not in results_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    
    result = results_cache[run_id]
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
    if run_id not in results_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    return results_cache[run_id]

@router.get("/runs/{run_id}/export/csv")
async def export_csv(run_id: str):
    if run_id not in results_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    # For MVP, we'll just return a simplified JSON for now or a CSV string
    # In a real app, use pandas.to_csv
    return {"message": "CSV export not fully implemented for streaming, but data available in JSON"}

@router.get("/runs/{run_id}/export/markdown")
async def export_markdown(run_id: str):
    if run_id not in results_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    
    result = results_cache[run_id]
    lines = [f"# CiteGraph-NLP Report: {run_id}", ""]
    lines.append(f"## Seed Paper: {result.seed_paper_id}")
    lines.append("")
    lines.append("### Foundational Papers")
    for i, p in enumerate(result.ranked_foundational_papers):
        lines.append(f"{i+1}. **{p['title']}** ({p['year']}) - Score: {p['score']:.2f}")
    
    return {"report": "\n".join(lines)}
