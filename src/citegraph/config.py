from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from urllib.parse import urlparse

#: An environment this application knows how to behave in. An unrecognised value
#: is reported rather than treated as development, because "production-ish" is how
#: an open API gets exposed.
KNOWN_ENVIRONMENTS = ("development", "production")

#: Passwords that are the vendor's default, or a word. A committed fallback is
#: obfuscation, and Neo4j's own default is `neo4j`.
PLACEHOLDER_PASSWORDS = ("neo4j", "password", "changeme", "change-me", "secret",
                         "example", "placeholder", "your_password")


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
    # False, not True. There is no GROBID service in the container this ships in,
    # and a default of True meant deploy-backend.yml had to force it off on every
    # deploy to stop the pipeline waiting on a service that is not there.
    enable_grobid: bool = False

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

    # Build identity, stamped by deploy-backend.yml at `docker run`. Absent when
    # the app is started by hand, and /version says so rather than inventing a
    # value: scripts/check_deployed_build.py refuses an unstamped build, which is
    # the only thing that polices it. A missing stamp is deliberately not a
    # startup refusal -- it is observability, and taking a working deployment
    # down over it would be the wrong trade.
    git_sha: str | None = None
    build_time: str | None = None

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

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    def problems(self) -> list[tuple[str, str]]:
        """Every configuration fault, as `(severity, sentence)`, gathered in one
        pass.

        Terminus B1: a boot that reports one fault per restart makes the operator
        fix them one at a time, and the ones after the first are never reached. So
        this collects, and `refuse_if_misconfigured` decides once.

        `fatal` means the process should not start. `report` means it should start
        and say so, because refusing would be worse than the fault.

        A missing GIT_SHA is deliberately not here. It is one question with one
        owner: `scripts/check_deployed_build.py` refuses an unstamped build. Taking
        a working deployment down over observability would be the wrong trade, and
        two guards for one question is the duplication Terminux 5.8 warns about.
        """
        found: list[tuple[str, str]] = []
        production = self.is_production

        if self.app_env.strip().lower() not in KNOWN_ENVIRONMENTS:
            found.append(("report", f"APP_ENV is {self.app_env!r}, which is neither "
                                    f"{' nor '.join(KNOWN_ENVIRONMENTS)}. Treat it as "
                                    f"development, where the API is open."))

        if production and not (self.api_key or "").strip():
            found.append(("fatal", "APP_ENV=production and API_KEY is empty, so every /api "
                                   "route is open to the internet. Set API_KEY."))
        if production and self.api_key and len(self.api_key.strip()) < 16:
            found.append(("fatal", f"API_KEY is {len(self.api_key.strip())} characters. "
                                   f"Use at least 16."))

        if "*" in self.cors_origin_list:
            found.append(("fatal" if production else "report",
                          "CORS_ORIGINS contains '*', so any page a browser visits can call "
                          "this API and read the response. List the origins instead."))
        if production and not self.cors_origin_list:
            found.append(("fatal", "APP_ENV=production and CORS_ORIGINS is empty, so the "
                                   "browser cannot call the API at all."))
        if production and any(origin.startswith("http://") for origin in self.cors_origin_list):
            found.append(("report", "CORS_ORIGINS lists a plaintext http:// origin in "
                                    "production, so those requests are not encrypted."))

        if self.enable_neo4j and not (self.neo4j_password or "").strip():
            found.append(("fatal" if production else "report",
                          "ENABLE_NEO4J is true and NEO4J_PASSWORD is empty, so the graph "
                          "store has no password. Set one or disable the profile."))
        if ((self.neo4j_password or "").strip().lower() in PLACEHOLDER_PASSWORDS
                and self.enable_neo4j):
            # Only a fault while the profile is on. A developer whose .env still
            # carries `NEO4J_PASSWORD=password` from a template, with neo4j
            # disabled, is not misconfigured -- and refusing to start there broke
            # the test suite on 2026-09-26, which is how it was found.
            found.append(("fatal", f"NEO4J_PASSWORD is {self.neo4j_password!r}, which is a "
                                   f"vendor default or a placeholder rather than a secret."))
        elif (self.neo4j_password or "").strip().lower() in PLACEHOLDER_PASSWORDS:
            found.append(("report", f"NEO4J_PASSWORD is {self.neo4j_password!r}, a "
                                    f"placeholder. It is unused while ENABLE_NEO4J is "
                                    f"false, and would be refused if it were not."))

        if self.enable_grobid and urlparse(self.grobid_url).hostname in ("localhost", "127.0.0.1", "::1"):
            found.append(("report", f"ENABLE_GROBID is true but GROBID_URL points at "
                                    f"{self.grobid_url}, and no GROBID service runs beside "
                                    f"this API. Point it at a real service or set "
                                    f"ENABLE_GROBID=false."))

        if production and not (self.openalex_email or "").strip():
            found.append(("report", "APP_ENV=production and OPENALEX_EMAIL is empty, so "
                                    "OpenAlex requests go through the anonymous pool. Set "
                                    "it for the polite pool."))

        for name, value, floor in (("DEFAULT_BACKWARD_DEPTH", self.default_backward_depth, 1),
                                   ("DEFAULT_FORWARD_DEPTH", self.default_forward_depth, 1),
                                   ("DEFAULT_MAX_TOTAL_PAPERS", self.default_max_total_papers, 1)):
            if value < floor:
                found.append(("fatal", f"{name} is {value}, which is not a usable limit."))
        if self.default_backward_depth > 10 or self.default_forward_depth > 10:
            found.append(("report", f"A default traversal depth above ten hops "
                                    f"(backward={self.default_backward_depth}, "
                                    f"forward={self.default_forward_depth}) will fan out "
                                    f"faster than a provider will answer."))
        if not 0.0 < self.weight_alpha < 1.0 or not 0.0 < self.weight_beta < 1.0:
            found.append(("fatal", f"WEIGHT_ALPHA={self.weight_alpha} and "
                                   f"WEIGHT_BETA={self.weight_beta}; both must be "
                                   f"between 0 and 1 for a convex combination."))
        return found

    def refuse_if_misconfigured(self) -> None:
        """Raise SystemExit if anything fatal is wrong. Reports the rest first, so
        a fault that is only a warning is visible even when a fatal one is not."""
        fatal = [(severity, text) for severity, text in self.problems() if severity == "fatal"]
        for severity, text in self.problems():
            if severity != "fatal":
                print(f"WARNING: {text}")
        if fatal:
            lines = "\n".join(f"  - {text}" for _, text in fatal)
            raise SystemExit(
                f"REFUSING TO START: {len(fatal)} configuration problem(s):\n{lines}\n"
                f"Set them in the environment, or set APP_ENV=development for a local run."
            )

settings = Settings()
