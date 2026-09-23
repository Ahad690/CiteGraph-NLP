from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from datetime import datetime, timezone
import uuid
import logging
import json
import asyncio
import csv
import io

import networkx as nx

from citegraph.models.paper import PaperQuery
from citegraph.models.run import RunResult
from citegraph.pipeline.orchestrator import PipelineOrchestrator
from citegraph.graph.builder import GraphBuilder
from citegraph.providers.base import close_shared_client
from citegraph.utils.tasks import task_manager

router = APIRouter()
orchestrator = PipelineOrchestrator()
logger = logging.getLogger(__name__)


def _md(value) -> str:
    """Escape a value for a markdown table cell.

    An unescaped pipe or newline in a title silently breaks the table layout.
    """
    if value is None:
        return "—"
    text = " ".join(str(value).split())
    return text.replace("|", r"\|")


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
    await close_shared_client()

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

# One lock per run for the read-modify-write below. The API runs as a single
# uvicorn worker (Dockerfile CMD has no --workers), so an in-process lock is
# enough to stop two papers opened at once from overwriting each other's update.
_result_locks: dict[str, asyncio.Lock] = {}


def _result_lock(run_id: str) -> asyncio.Lock:
    lock = _result_locks.get(run_id)
    if lock is None:
        lock = _result_locks[run_id] = asyncio.Lock()
    return lock


@router.post("/runs/{run_id}/technical-evidence")
async def recover_technical_evidence(run_id: str, paper_id: str):
    """Read one computer-science paper's arXiv PDF for a dataset count.

    The dashboard calls this when a user opens a paper whose abstract stated no
    count. It used to happen inside every run for up to ten papers, which cost
    about 27 seconds because arXiv allows one request every three seconds. The
    outcome is saved into the run, found or not, so reopening the paper does not
    fetch the PDF again.

    `paper_id` is a query parameter rather than a path segment because paper
    ids are usually DOIs, and DOIs contain slashes.
    """
    result = await _load_result(run_id)
    paper = next((p for p in result.papers if p.paper_id == paper_id), None)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not in this run")
    current = next((t for t in result.technical_evidence if t.paper_id == paper_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="No dataset evidence is tracked for this paper")

    already_checked = "technical_full_text" in paper.provenance
    if current.status != "missing" or not paper.arxiv_id or already_checked:
        return {"technical_evidence": current, "fetched": False,
                "checked": already_checked}

    recovered = await orchestrator.recover_technical_from_full_text(paper)
    record = {
        "provider": "arxiv",
        "arxiv_id": paper.arxiv_id,
        "found": recovered is not None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # Re-read inside the lock: another paper may have been updated while the
    # PDF was downloading, and writing back the copy loaded above would undo it.
    async with _result_lock(run_id):
        latest = await _load_result(run_id)
        for stored in latest.papers:
            if stored.paper_id == paper_id:
                stored.provenance["technical_full_text"] = record
        if recovered is not None:
            latest.technical_evidence = [
                recovered if item.paper_id == paper_id else item
                for item in latest.technical_evidence
            ]
        await store.save_result(run_id, latest)

    return {"technical_evidence": recovered or current, "fetched": True, "checked": True}


def _attachment(content: str, media_type: str, run_id: str, extension: str,
                *, bom: bool = False) -> Response:
    """Return export content as a real downloadable file.

    These used to return {"csv": "..."} / {"report": "..."}. The frontend saves
    the response body straight to disk as citegraph-<id>.csv, so users got a
    .csv file whose contents were a JSON envelope with the whole table escaped
    onto one line -- unopenable in Excel.
    """
    body = ("﻿" + content) if bom else content
    return Response(
        content=body.encode("utf-8"),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="citegraph-{run_id}.{extension}"'},
    )


async def _load_result(run_id: str) -> RunResult:
    data = await store.get_run(run_id)
    if not data or not data.get("result_json"):
        raise HTTPException(status_code=404, detail="Run not found or not completed")
    return RunResult.model_validate_json(data["result_json"])


@router.get("/runs/{run_id}/export/json")
async def export_json(run_id: str):
    data = await store.get_run(run_id)
    if not data or not data.get("result_json"):
        raise HTTPException(status_code=404, detail="Run not found or not completed")
    # Re-indent so a downloaded .json file is readable rather than one long line.
    pretty = json.dumps(json.loads(data["result_json"]), indent=2, ensure_ascii=False)
    return _attachment(pretty, "application/json", run_id, "json")


@router.get("/runs/{run_id}/export/csv")
async def export_csv(run_id: str):
    result = await _load_result(run_id)

    resolutions = {r.paper_id: r for r in result.population_resolutions}
    technical = {item.paper_id: item for item in result.technical_evidence}
    in_degree: Dict[str, int] = {}
    out_degree: Dict[str, int] = {}
    for edge in result.citation_edges:
        out_degree[edge.source_paper_id] = out_degree.get(edge.source_paper_id, 0) + 1
        in_degree[edge.target_paper_id] = in_degree.get(edge.target_paper_id, 0) + 1
    ranks = {
        entry.get("paper_id"): idx
        for idx, entry in enumerate(result.ranked_foundational_papers, start=1)
    }

    buffer = io.StringIO()
    # QUOTE_ALL + the csv module handles embedded quotes, commas and newlines
    # that the old hand-rolled f-string broke on (journal was never escaped).
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow([
        "paper_id", "title", "authors", "year", "journal", "doi", "pmid",
        "n_eff", "population_status", "population_confidence",
        "research_domain", "research_field", "dataset_examples", "dataset_unit", "dataset_kind", "dataset_status", "dataset_confidence", "dataset_evidence",
        "cited_by_in_graph", "references_in_graph", "foundational_rank",
        "is_seed",
    ])
    for paper in result.papers:
        res = resolutions.get(paper.paper_id)
        dataset = technical.get(paper.paper_id)
        writer.writerow([
            paper.paper_id,
            paper.title or "",
            "; ".join(paper.authors[:5]) + ("; et al." if len(paper.authors) > 5 else ""),
            paper.year or "",
            paper.journal or "",
            paper.doi or "",
            paper.pmid or "",
            res.n_eff if res and res.n_eff is not None else "",
            res.status if res else "",
            f"{res.confidence:.2f}" if res else "",
            paper.research_domain,
            paper.research_field or "",
            dataset.value if dataset and dataset.value is not None else "",
            dataset.unit if dataset and dataset.unit else "",
            dataset.kind if dataset and dataset.kind else "",
            dataset.status if dataset else "",
            f"{dataset.confidence:.2f}" if dataset else "",
            dataset.evidence if dataset and dataset.evidence else "",
            in_degree.get(paper.paper_id, 0),
            out_degree.get(paper.paper_id, 0),
            ranks.get(paper.paper_id, ""),
            "yes" if paper.paper_id == result.seed_paper_id else "no",
        ])

    # Excel assumes the system codepage without a BOM, mangling accented names.
    return _attachment(buffer.getvalue(), "text/csv", run_id, "csv", bom=True)


@router.get("/runs/{run_id}/export/edges.csv")
async def export_edges_csv(run_id: str):
    """Edge list as its own CSV -- the paper CSV cannot represent the graph."""
    result = await _load_result(run_id)
    titles = {p.paper_id: (p.title or "") for p in result.papers}

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow([
        "source_paper_id", "source_title", "target_paper_id", "target_title",
        "final_weight", "base_weight", "n_score", "journal_score",
        "edge_confidence", "providers",
    ])
    for edge in result.citation_edges:
        writer.writerow([
            edge.source_paper_id, titles.get(edge.source_paper_id, ""),
            edge.target_paper_id, titles.get(edge.target_paper_id, ""),
            f"{edge.final_weight:.4f}" if edge.final_weight is not None else "",
            f"{edge.base_weight:.4f}" if edge.base_weight is not None else "",
            f"{edge.n_score:.4f}" if edge.n_score is not None else "",
            f"{edge.journal_score:.4f}" if edge.journal_score is not None else "",
            f"{edge.confidence:.2f}",
            "; ".join(edge.providers),
        ])
    return _attachment(buffer.getvalue(), "text/csv", f"{run_id}-edges", "csv", bom=True)


@router.get("/runs/{run_id}/export/graphml")
async def export_graphml(run_id: str):
    """GraphML for Gephi/yEd. The frontend already offered this format but no
    route existed, so the button returned 404."""
    result = await _load_result(run_id)
    graph = GraphBuilder().build(
        result.papers, result.citation_edges, result.population_resolutions
    )
    # GraphML has no null: drop unset attributes rather than emit "None".
    for _node, attrs in graph.nodes(data=True):
        for key in [k for k, v in attrs.items() if v is None]:
            del attrs[key]
    for _u, _v, attrs in graph.edges(data=True):
        for key in [k for k, v in attrs.items() if v is None]:
            del attrs[key]

    buffer = io.BytesIO()
    nx.write_graphml(graph, buffer)
    return Response(
        content=buffer.getvalue(),
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="citegraph-{run_id}.graphml"'},
    )

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

    papers = {p.paper_id: p for p in result.papers}
    seed = papers.get(result.seed_paper_id)
    resolved = [r for r in result.population_resolutions if r.n_eff is not None]
    clinical_applicable = sum(r.status != "not_applicable" for r in result.population_resolutions)
    technical_resolved = [item for item in result.technical_evidence if item.value is not None]

    lines = ["# CiteGraph-NLP Analysis Report", ""]
    if seed:
        lines.append(f"## {_md(seed.title)}")
        byline = ", ".join(seed.authors[:4]) + (" et al." if len(seed.authors) > 4 else "")
        if byline:
            lines.append(f"*{_md(byline)}*")
        venue = " · ".join(str(v) for v in (seed.journal, seed.year) if v)
        if venue:
            lines.append(f"{_md(venue)}")
        lines.append("")
    lines += [
        f"- **Run ID**: `{run_id}`",
        f"- **Seed paper**: `{result.seed_paper_id}`",
        f"- **Generated**: {generated_at}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Papers in graph | {len(result.papers)} |",
        f"| Citation edges | {len(result.citation_edges)} |",
        f"| Papers with clinical population evidence | {len(resolved)} of {clinical_applicable} applicable |",
        f"| Computer-science papers with dataset counts | {len(technical_resolved)} of {len(result.technical_evidence)} |",
        f"| Foundational candidates ranked | {len(result.ranked_foundational_papers)} |",
        f"| Citation paths ranked | {len(result.ranked_paths)} |",
        "",
    ]

    lines += ["## Probable Foundational Papers", ""]
    if result.ranked_foundational_papers:
        lines += ["| Rank | Title | Year | Score | Clinical N_eff |", "| ---: | --- | ---: | ---: | ---: |"]
        for i, p in enumerate(result.ranked_foundational_papers, start=1):
            n_eff = p.get("n_eff")
            lines.append(
                f"| {i} | {_md(p.get('title'))} | {p.get('year') or '—'} "
                f"| {float(p.get('score') or 0):.3f} | {n_eff if n_eff else '—'} |"
            )
    else:
        lines.append("_No foundational candidates were ranked for this run._")
    lines.append("")

    if result.technical_evidence:
        lines += ["## Computer-Science Dataset Evidence", "",
                  "Dataset counts are extracted from abstracts or linked arXiv PDFs and are not comparable with patient populations or used in ranking weights.", "",
                  "| Paper | Count | Unit | Kind | Status | Confidence |",
                  "| --- | ---: | --- | --- | --- | ---: |"]
        for item in result.technical_evidence:
            paper = papers.get(item.paper_id)
            lines.append(
                f"| {_md(paper.title if paper else item.paper_id)} | {item.value if item.value is not None else '—'} "
                f"| {_md(item.unit)} | {_md(item.kind)} | {item.status} | {item.confidence:.2f} |"
            )
        lines.append("")

    lines += ["## Population Evidence", ""]
    if resolved:
        lines += ["| Paper | N_eff | Type | Status | Confidence |",
                  "| --- | ---: | --- | --- | ---: |"]
        for res in sorted(resolved, key=lambda r: r.n_eff or 0, reverse=True):
            paper = papers.get(res.paper_id)
            label = _md(paper.title) if paper and paper.title else f"`{res.paper_id}`"
            lines.append(
                f"| {label} | {res.n_eff} | {res.semantic_type or '—'} "
                f"| {res.status} | {res.confidence:.2f} |"
            )
    elif clinical_applicable == 0:
        lines.append("_Clinical population size is not applicable to the papers in this run._")
    else:
        lines.append(
            "_No sample sizes were extracted. Extraction targets clinical-trial "
            "phrasing (\"N patients were randomized\"), so papers outside that "
            "domain typically yield none, and citation edges fall back to a "
            "uniform structural weight._"
        )
    lines.append("")

    if result.ranked_paths:
        lines += ["## Top Citation Paths", ""]
        for path in result.ranked_paths[:5]:
            titles = path.get("titles") or path.get("paper_ids") or []
            lines.append(
                f"{path.get('rank', '?')}. **score {float(path.get('path_score') or 0):.3f}** "
                f"({path.get('path_length', len(titles) - 1)} hops)"
            )
            for step, title in enumerate(titles):
                arrow = "" if step == 0 else "→ "
                lines.append(f"   - {arrow}{_md(title)}")
            lines.append("")

    lines += [
        "---", "",
        "_Rankings are probabilistic (PageRank over citation weights "
        "plus age and applicable clinical-evidence bonuses), not a definitive claim of "
        "originality. Review the underlying papers before citing._",
    ]
    return _attachment("\n".join(lines), "text/markdown", run_id, "md")
