import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from citegraph.pipeline.orchestrator import PipelineOrchestrator
from citegraph.models.paper import PaperQuery
from citegraph.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

async def main():
    orchestrator = PipelineOrchestrator()
    
    # Use a real DOI for demo if possible, or a mock
    # This DOI is from a well-known JAMA paper
    doi = "10.1001/jama.2023.1234" 
    
    logger.info(f"Running demo for DOI: {doi}")
    
    query = PaperQuery(query_type="doi", value=doi)
    
    try:
        result = await orchestrator.run(query, backward_depth=1, max_papers=5)
        
        print("\n=== Run Results ===")
        print(f"Run ID: {result.run_id}")
        print(f"Papers Found: {len(result.papers)}")
        print(f"Citation Edges: {len(result.citation_edges)}")
        
        print("\n=== Top Foundational Papers ===")
        for i, paper in enumerate(result.ranked_foundational_papers):
            print(f"{i+1}. {paper['title']} ({paper['year']}) - Score: {paper['score']:.4f}")
            
        print("\n=== Population Resolutions ===")
        for res in result.population_resolutions[:5]:
            print(f"Paper: {res.paper_id} | N_eff: {res.n_eff} | Status: {res.status}")
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
