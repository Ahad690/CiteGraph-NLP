from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    # API security.
    # api_key: when set, every /api route requires a matching X-API-Key header.
    # Left unset the API is open, which is fine for a local demo but must be
    # configured before exposing the service publicly.
    api_key: str | None = None
    # Comma-separated list of browser origins allowed to call the API.
    # Set this to the deployed frontend origin (e.g. the Cloudflare Pages URL).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # API keys
    openalex_email: str | None = None
    semantic_scholar_api_key: str | None = None
    ncbi_api_key: str | None = None

    # Provider toggles
    enable_openalex: bool = True
    enable_crossref: bool = True
    enable_europe_pmc: bool = True
    enable_pubmed: bool = False
    enable_semantic_scholar: bool = False
    enable_clinical_trials: bool = False
    enable_unpaywall: bool = False

    # GROBID
    grobid_url: str = "http://localhost:8070"
    enable_grobid: bool = True

    # Storage
    data_dir: Path = Path("./data")
    sqlite_path: Path = Path("./data/cache/citegraph.sqlite")

    # Graph
    enable_neo4j: bool = False
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    # No default: a shipped password would become the real one the first time
    # anyone enables the neo4j profile without setting NEO4J_PASSWORD.
    neo4j_password: str | None = None

    # Traversal defaults
    default_backward_depth: int = 2
    default_forward_depth: int = 1
    default_max_total_papers: int = 100

    # Weighting defaults
    weight_alpha: float = 0.75
    weight_beta: float = 0.25
    n_reference: int = 100000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        """Allowed browser origins, parsed from the comma-separated setting."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
