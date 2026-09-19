# Appendix G: Selected Code Listings

Extracts from the delivered system, chosen because each embodies a decision
argued elsewhere in the thesis. Listings are lightly trimmed for width;
comments are as committed.

## G.1 Per-span ignore matching (Section 5.5)

The correction that recovered most of the extraction recall. The original
evaluated ignore patterns against the whole sentence and skipped every candidate
in it.

```python
for sentence in sentences:
    # Locate the spans that must not be read as population sizes (years,
    # percentages, p-values, dosages). These are matched per-span rather
    # than per-sentence: skipping the whole sentence discarded every
    # genuine count that merely shared a sentence with a date, which is
    # most of them ("...1099 patients ... through January 29, 2020").
    ignore_spans = [
        match.span()
        for ignore_p in IGNORE_PATTERNS
        for match in re.finditer(ignore_p, sentence)
    ]

    for pattern_info in POPULATION_PATTERNS:
        for match in re.finditer(pattern_info["pattern"], sentence, re.IGNORECASE):
            # Only reject when the captured number itself sits inside an
            # ignored span, not when one appears elsewhere in the sentence.
            number_start, number_end = match.span(1)
            if any(start < number_end and number_start < end
                   for start, end in ignore_spans):
                continue
            ...
```

## G.2 Edge weighting (Section 5.6)

```python
base_weight = (self.alpha * n_score) + (self.beta * journal_score)

# Confidence scales the *population evidence* only. Multiplying the
# whole base weight by it collapsed every edge to exactly 0.0 for any
# paper where extraction found nothing -- which is every paper outside
# clinical-trial phrasing. The journal term is structural and always
# applies, so an edge without population evidence keeps a small uniform
# weight instead of vanishing.
pop_confidence = target_res.confidence if target_res else 0.5
evidence_term = self.alpha * n_score * pop_confidence
final_weight = (evidence_term + (self.beta * journal_score)) * edge.confidence
```

And the fallback in the graph builder that had concealed the defect:

```python
# `or 1.0` would silently rewrite a genuine 0.0 weight to 1.0,
# which hid the fact that every edge was being zeroed out.
weight=edge.final_weight if edge.final_weight is not None else 1.0,
```

## G.3 Identity aliasing and duplicate merging (Section 4.4.2)

```python
def _register(self, paper: Paper) -> None:
    """Store a paper and map every identifier it carries onto its paper_id."""
    self.papers[paper.paper_id] = paper
    self.visited.add(paper.paper_id)
    for raw in (paper.paper_id, paper.doi, paper.pmid,
                paper.pmcid, paper.openalex_id):
        if raw:
            self._aliases[IdCanonicalizer.canonicalize(raw)] = paper.paper_id
    key = self.title_key(paper.title)
    if key:
        self._title_keys.setdefault(key, paper.paper_id)


@classmethod
def title_key(cls, title: Optional[str]) -> Optional[str]:
    """A comparison key for detecting the same work under two identifiers.

    Sources occasionally hold two records for one article under different
    DOIs -- typically the clean version and one with front matter merged
    into the title ("...coronavirus infection1 1The authors thank..."). The
    titles share a long prefix, so compare a normalised prefix rather than
    the whole string. Returns None for titles too short to match safely.
    """
    if not title:
        return None
    normalised = " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())
    if len(normalised) < cls.MIN_TITLE_KEY_LENGTH:
        return None
    return normalised[: cls.TITLE_KEY_PREFIX]
```

## G.4 Commit-time edge filtering (Section 4.4.2)

The guarantee behind the zero-dangling-edge result in Section 6.5.

```python
def _commit_edges(self, raw_edges, direction) -> None:
    """Rewrite edge endpoints to canonical ids and keep only resolved ones."""
    dropped = 0
    for edge in raw_edges:
        source = self._canonical(edge.source_paper_id)
        target = self._canonical(edge.target_paper_id)
        if not source or not target or source == target:
            dropped += 1
            continue
        key = (source, target)
        if key in self._edge_keys:
            continue
        self._edge_keys.add(key)
        edge.source_paper_id = source
        edge.target_paper_id = target
        edge.edge_id = f"{source}_cites_{target}"
        self.edges.append(edge)
```

## G.5 Null-safe provider mapping (Section 5.4)

```python
@staticmethod
def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Fetch a nested object, treating an explicit null as an empty object.

    OpenAlex returns ``"primary_location": {"source": null}`` for works with
    no indexed venue (roughly half the results in some queries), and
    ``dict.get(key, {})`` returns None in that case because the key exists.
    """
    value = data.get(key)
    return value if isinstance(value, dict) else {}
```

With per-record isolation so one malformed work cannot discard its batch:

```python
for work in data.get("results", []):
    work_id = self.openalex_id_of(work)
    if not work_id:
        continue
    try:
        papers[work_id] = self._map_to_paper(work)
    except Exception as e:
        # Isolate per-record faults: one malformed work must not
        # discard the other 49 in the batch.
        logger.warning("Skipping unmappable OpenAlex work %s: %s", work_id, e)
```

## G.6 SSRF guard (Section 5.7)

```python
@staticmethod
async def _resolves_to_public_address(url: str) -> bool:
    """True when every address the URL's host resolves to is public.

    The URL here comes straight from the API request body, so without this
    check the server can be pointed at loopback, link-local (cloud metadata)
    or RFC1918 addresses and made to issue requests from inside the trust
    boundary.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError):
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (address.is_private or address.is_loopback or address.is_link_local
                or address.is_reserved or address.is_multicast
                or address.is_unspecified):
            return False
    return True
```

Redirects are followed manually so each hop is re-validated; a public host that
redirects to an internal one is refused at the second hop.

## G.7 Bounded path enumeration (Section 4.12)

```python
def _iter_paths(self, seed_id: str, cutoff: int = 4):
    """Yield every simple path leaving the seed, in a single traversal.

    Calling ``nx.all_simple_paths(seed, target)`` once per target re-walks
    the entire reachable subgraph for every node in the graph, so the cost
    is multiplied by the node count while producing the same set of paths.
    One depth-limited DFS yields each path exactly once.
    """
    stack = [[seed_id]]
    while stack:
        path = stack.pop()
        if len(path) > 1:
            yield path
        if len(path) - 1 >= cutoff:
            continue
        for successor in self.graph.successors(path[-1]):
            # Paths are at most cutoff+1 long, so a scan beats a set here.
            if successor not in path:
                stack.append(path + [successor])
```

## G.8 Retry policy (Section 5.4)

```python
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def is_transient_error(exc: BaseException) -> bool:
    """True when a failed provider call is worth retrying.

    A 404 means the provider simply does not hold that record, which is
    routine for Crossref and Europe PMC. Retrying it cannot change the
    answer and costs the exponential-backoff budget on every miss, so only
    rate limits, server faults and transport errors are retried.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exc, (httpx.TransportError, httpx.StreamError))
```

## G.9 Pooled HTTP client (Section 6.6.3)

```python
# One pooled client for every outbound provider call. Creating a client per
# request (the previous `async with httpx.AsyncClient(...)` in each _get)
# meant a fresh TCP and TLS handshake every time: measured at ~634 ms of
# pure overhead per request, 58% of the time each call took.
_shared_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()

HTTP_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)
HTTP_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


async def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        async with _client_lock:
            if _shared_client is None or _shared_client.is_closed:
                _shared_client = httpx.AsyncClient(
                    timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS)
    return _shared_client
```

## G.10 Evaluation metric definitions (Section 3.5.3)

```python
def wilson_interval(successes: int, trials: int, z: float = 1.96):
    """95% Wilson score interval.

    Reported instead of a bare proportion because the gold set is small; a
    normal approximation is unreliable at n=20 and degenerates at 0% or 100%.
    """
    if trials == 0:
        return None
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    margin = z * ((p * (1 - p) / trials
                   + z * z / (4 * trials * trials)) ** 0.5) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))
```
