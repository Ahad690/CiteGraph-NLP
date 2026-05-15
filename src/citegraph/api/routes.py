from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict
import uuid

from citegraph.models.paper import PaperQuery
from citegraph.models.run import RunResult
from citegraph.pipeline.orchestrator import PipelineOrchestrator

router = APIRouter()
orchestrator = PipelineOrchestrator()

# Store results in memory for MVP (could be SQLite/Redis later)
results_cache: Dict[str, RunResult] = {}

class RunRequest(PaperQuery):
    backward_depth: int = 2
    forward_depth: int = 1
    max_total_papers: int = 100
    use_pdf_parsing: bool = True

@router.post("/runs", response_model=Dict[str, str])
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    
    # For MVP, we'll run it synchronously if it's small, 
    # but let's implement the background task pattern.
    background_tasks.add_task(execute_run, run_id, request)
    
    return {"run_id": run_id, "status": "started"}

async def execute_run(run_id: str, request: RunRequest):
    try:
        query = PaperQuery(
            query_type=request.query_type,
            value=request.value,
            pdf_path=request.pdf_path
        )
        result = await orchestrator.run(
            query=query,
            backward_depth=request.backward_depth,
            forward_depth=request.forward_depth,
            max_papers=request.max_total_papers
        )
        # In a real app, we'd save this to a database
        results_cache[run_id] = result
    except Exception as e:
        # Log error
        print(f"Run {run_id} failed: {e}")

@router.get("/runs/{run_id}", response_model=RunResult)
async def get_run(run_id: str):
    if run_id not in results_cache:
        raise HTTPException(status_code=404, detail="Run not found or still processing")
    return results_cache[run_id]

@router.get("/runs/{run_id}/graph")
async def get_graph(run_id: str):
    if run_id not in results_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    
    result = results_cache[run_id]
    # Format for a frontend graph library (like react-force-graph or cytoscape)
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
