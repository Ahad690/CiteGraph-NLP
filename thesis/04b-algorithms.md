# Chapter 4 (continued): Algorithm Specifications

This chapter states the five core algorithms precisely enough to be
reimplemented. Each is given as pseudocode with its complexity, its failure
modes, and a note on the design decisions that are not obvious from the code.

## 4.8 Algorithm 1: metadata merge

### 4.8.1 Problem

Three providers return partially overlapping, sometimes conflicting records for
one work. Produce a single record, preferring the more reliable source per
field, and retain enough provenance that a disagreement can be investigated.

### 4.8.2 Specification

```
INPUT   results: map from provider name to ProviderResult
OUTPUT  Paper

 1  papers <- { name: r.paper  for name, r in results  if r.paper is not null }
 2  if papers is empty then
 3      raise ResolutionError("no provider returned a record")
 4
 5  # Canonical identity: DOI first, since it is the identifier all three share.
 6  primary_doi        <- first non-null doi        over papers
 7  primary_pmid       <- first non-null pmid       over papers
 8  primary_openalex   <- first non-null openalex_id over papers
 9  paper_id <- primary_doi or primary_pmid or primary_openalex
10
11  # Field-level precedence. Crossref carries publisher-deposited
12  # bibliographic metadata; OpenAlex reconstructs abstracts.
13  title    <- first non-null title    over [crossref, openalex, europe_pmc]
14  year     <- first non-null year     over [crossref, openalex, europe_pmc]
15  authors  <- first non-empty authors over [crossref, openalex, europe_pmc]
16  journal  <- first non-null journal  over [crossref, openalex, europe_pmc]
17  abstract <- first non-null abstract over [openalex, europe_pmc, crossref]
18
19  provenance <- { name: p.provenance[name]  for name, p in papers }
20  source_ids <- union of p.source_ids over papers
21  confidence <- 0.95 if |papers| > 1 else 0.80
22
23  return Paper(paper_id, primary_doi, primary_pmid, primary_openalex,
24               title, authors, year, journal, abstract,
25               source_ids, confidence, provenance)
```

### 4.8.3 Complexity and notes

O(*p* · *f*) for *p* providers and *f* fields; *p* = 3 and *f* is fixed, so the
merge is effectively constant time. The cost of resolution is entirely the
network I/O that precedes it, which is why the three provider queries are issued
concurrently (Section 4.3.1).

The confidence heuristic at line 21, 0.95 when more than one provider returned
a record, 0.80 otherwise, is agreement-as-confidence, and it is weak. It
rewards two providers *returning* a record, not two providers *agreeing* on its
contents. A stronger formulation would compare the fields themselves and reduce
confidence on disagreement. This is not implemented.

## 4.9 Algorithm 2: level-synchronous citation traversal

### 4.9.1 Problem

Expand outward from a seed paper in both directions to bounded depth, under a
bounded total number of papers, collapsing multiple identifiers for one work
onto a single node, and emitting no edge whose endpoints are not both present.

### 4.9.2 Specification

```
INPUT   seed, backward_depth, forward_depth, max_papers
OUTPUT  papers: map paper_id -> Paper,  edges: list of CitationEdge

 1  register(seed)                       # stores paper + all its aliases
 2  frontier[backward] <- [seed.id] if backward_depth > 0 else []
 3  frontier[forward]  <- [seed.id] if forward_depth  > 0 else []
 4  budget <- allocate(backward_depth, forward_depth, max_papers)
 5  spent  <- { backward: 0, forward: 0 }
 6
 7  for depth in 0 .. max(backward_depth, forward_depth) - 1 do
 8      for direction in [backward, forward] do
 9          if depth >= depth_limit[direction] or frontier[direction] empty then
10              frontier[direction] <- []; continue
11          if |papers| >= max_papers then
12              frontier[direction] <- []; continue
13
14          # Release the other direction's reservation once it is exhausted,
15          # so a paper with no citing works still gets a full reference tree.
16          other <- the opposite direction
17          if frontier[other] non-empty and depth < depth_limit[other] then
18              allowance <- budget[direction] - spent[direction]
19          else
20              allowance <- max_papers - |papers|
21          if allowance <= 0 then frontier[direction] <- []; continue
22
23          limit <- min(max_papers, |papers| + allowance)
24          before <- |papers|
25          frontier[direction] <- EXPAND(frontier[direction], direction, limit)
26          spent[direction] <- spent[direction] + (|papers| - before)
27
28  return papers, edges
```

`EXPAND` is where the batching lives:

```
EXPAND(frontier, direction, limit):
 1  # One request per frontier paper, issued concurrently (semaphore = 5).
 2  raw_edges <- concurrent_fetch(frontier, direction)
 3  if raw_edges empty then return []
 4
 5  # Collect every neighbour identifier not already resolved.
 6  pending <- []
 7  for edge in raw_edges do
 8      n <- edge.target if direction = backward else edge.source
 9      if canonical(n) is null and n not in unresolvable then
10          append canonicalise(n) to pending
11
12  added <- []
13  if pending non-empty and |papers| < limit then
14      added <- RESOLVE_BATCH(pending, limit)
15
16  COMMIT_EDGES(raw_edges, direction)
17  return added
```

```
RESOLVE_BATCH(pending, limit):
 1  partition pending into work_ids (W...), dois (10....), others
 2
 3  # 50 identifiers per request instead of one request per paper.
 4  if work_ids non-empty then
 5      for paper in openalex.batch_by_work_id(work_ids) do ABSORB(paper)
 6  if dois non-empty then
 7      for paper in openalex.batch_by_doi(dois)      do ABSORB(paper)
 8
 9  # Only identifiers the batch endpoints missed reach the slow path.
10  leftovers <- pending not resolved above
11  for paper in concurrent_resolve_full(leftovers) do ABSORB(paper)
12
13  mark every still-unresolved identifier as unresolvable
14  return newly added paper_ids
```

```
ABSORB(raw_id, paper):
 1  if paper.paper_id not already stored then
 2      # Duplicate check runs BEFORE the budget check, so a merged
 3      # duplicate never consumes one of the max_papers slots.
 4      dup <- duplicate_of(paper)          # title-prefix + year agreement
 5      if dup is not null then
 6          alias(paper.paper_id -> dup); alias(raw_id -> dup)
 7          duplicates_merged <- duplicates_merged + 1
 8          return
 9      if |papers| >= limit then return
10      register(paper); append paper.paper_id to added
11  alias(raw_id -> paper.paper_id)
```

```
COMMIT_EDGES(raw_edges, direction):
 1  for edge in raw_edges do
 2      s <- canonical(edge.source);  t <- canonical(edge.target)
 3      # An edge is emitted only if BOTH endpoints resolved. This is what
 4      # guarantees zero dangling edges in the output.
 5      if s is null or t is null or s = t then continue
 6      if (s, t) already emitted then continue
 7      rewrite edge endpoints to (s, t); append to edges
```

### 4.9.3 Complexity

Let *N* be `max_papers` and *F* the mean out-degree per expanded paper.

- Edge fetches: one request per frontier paper, O(*N*) requests in the worst
  case, issued with concurrency 5.
- Metadata fetches: O(*N* / 50) batched requests: the decisive improvement.
  The pre-batching implementation issued O(*N*) individual resolutions, each
  querying three providers, for O(3*N*) requests.
- Edge dedup: O(1) per edge via a hash set of committed pairs. The original
  implementation scanned the committed list linearly per edge, which is O(*E*²).

### 4.9.4 Failure modes handled

| Failure | Handling |
|---------|----------|
| Provider returns an unparseable identifier | Recorded as unresolvable; not retried on later levels |
| One malformed record in a batch of 50 | Per-record try/except; the other 49 survive (§5.4) |
| Same work under two identifiers | Alias table collapses them to one node |
| Same work under two DOIs with near-identical titles | Title-prefix match with year agreement |
| A heavily cited seed | Forward results are sorted by citation count and capped |

## 4.10 Algorithm 3: population candidate extraction

### 4.10.1 Specification

```
INPUT   paper_id, text, section
OUTPUT  list of PopulationCandidate

 1  if text is empty then return []
 2  sentences <- split(text)              # spaCy if available, else regex
 3  candidates <- []
 4
 5  for sentence in sentences do
 6      # Spans that must not be read as populations: years, percentages,
 7      # p-values, dosages. Computed per span, NOT per sentence -- see 4.10.3.
 8      ignore_spans <- { match.span()
 9                        for pattern in IGNORE_PATTERNS
10                        for match in finditer(pattern, sentence) }
11
12      for pat in POPULATION_PATTERNS do
13          for m in finditer(pat.regex, sentence, IGNORECASE) do
14              (ns, ne) <- m.span(1)          # span of the captured number
15              if (ns, ne) overlaps any ignore_span then continue
16              value <- int(strip_separators(m.group(1)))
17              if value <= 0 or value > 10_000_000 then continue
18              confidence <- min(1.0, pat.weight + section_bonus(section))
19              append PopulationCandidate(value, m.group(0), sentence,
20                                         section, pat.type, ns, ne,
21                                         confidence) to candidates
22
23  return candidates
```

### 4.10.2 Complexity

O(*S* · *P* · *L*) for *S* sentences, *P* patterns (20) and sentence length *L*.
Linear in text length for a fixed pattern set. Measured at roughly 200 ms per
abstract (Section 6.6.1), which is slow for regular expressions and is dominated
by spaCy sentence segmentation rather than by matching.

### 4.10.3 The span-versus-sentence decision

Lines 8–15 encode the single most consequential correction made to this
algorithm. The original implementation evaluated the ignore patterns against
the *whole sentence* and skipped every candidate in it on a match. Because
`IGNORE_PATTERNS` contains `\b20\d{2}\b`, and clinical abstracts mention a year
in most sentences, the rule discarded the very numbers it existed to protect.
Section 5.5 gives the measurement. Evaluating per span preserves the intent, a
year is never read as a population, without the collateral loss.

## 4.11 Algorithm 4: population resolution

### 4.11.1 Specification

```
INPUT   paper_id, candidates
OUTPUT  PopulationResolution

 1  if candidates empty then
 2      return Resolution(n_eff=null, confidence=0.0, status="missing")
 3
 4  filtered <- [ c in candidates if c.confidence > 0.40 ]
 5  if filtered empty then
 6      return Resolution(n_eff=null, confidence=0.0, status="missing")
 7
 8  # Score combines extraction confidence with the clinical informativeness
 9  # of the semantic type: a randomised total outranks an arm size.
10  score(c) = c.confidence * (1 + TYPE_PRIORITY[c.semantic_type] / 10)
11
12  best <- argmax(filtered, score)
13
14  # Ambiguity: a rival scoring within 10% but differing materially in value
15  # signals an unclear abstract, not a system failure.
16  ambiguous <- exists c in filtered, c != best, such that
17                   score(c) > 0.9 * score(best)
18               and |c.value - best.value| > 0.1 * best.value
19
20  return Resolution(n_eff=best.value, semantic_type=best.semantic_type,
21                    confidence=best.confidence,
22                    status = "ambiguous" if ambiguous else "resolved")
```

with type priorities: `TOTAL_RANDOMIZED` 10, `TOTAL_ANALYZED` 9,
`TOTAL_ENROLLED` 8, `SAMPLE_SIZE_GENERIC` 7, `ARM_SIZE` 5, `SCREENED` 4,
`COMPLETERS` 3, `FOLLOWUP_COUNT` 2, `EVENT_COUNT` 1, `UNKNOWN_NUMERIC` 0.

### 4.11.2 Known weakness

This algorithm produced the single value error in the evaluation (Section
6.4.2). For a case series of 138 patients whose abstract also reports many
subgroup counts, the selection returned 36. The scoring rewards pattern
confidence and type priority but has no notion of *which number the abstract is
about*, a subgroup count matched by a high-priority pattern outranks the cohort
total matched by a lower-priority one. Position in the abstract, and the
relationship between competing values, are both unused signals.

## 4.12 Algorithm 5: bounded path ranking

### 4.12.1 Problem

Rank citation paths from the seed by evidential strength, returning the top *k*,
without enumerating a combinatorial number of paths.

### 4.12.2 Specification

```
INPUT   graph, seed_id, top_n = 10, cutoff = 4
OUTPUT  ranked list of at most top_n paths

 1  if seed_id not in graph then return []
 2  heap <- empty min-heap ordered by score, capacity top_n
 3  examined <- 0
 4
 5  # ONE depth-first traversal yields every simple path from the seed.
 6  # Calling all_simple_paths(seed, target) per target re-walks the whole
 7  # reachable subgraph once per node -- see 4.12.3.
 8  stack <- [ [seed_id] ]
 9  while stack non-empty do
10      path <- pop(stack)
11      if |path| > 1 then
12          examined <- examined + 1
13          if examined > MAX_PATHS_EXAMINED then
14              log truncation; break
15          score <- SCORE_PATH(path)
16          if |heap| < top_n then push(heap, score, path)
17          else if score > min(heap).score then replace_min(heap, score, path)
18      if |path| - 1 >= cutoff then continue
19      for succ in successors(last(path)) do
20          if succ not in path then push(stack, path + [succ])
21
22  # Build result dictionaries only for the survivors, not for every path.
23  return sorted(heap, by score desc)
```

```
SCORE_PATH(path):
 1  weights     <- [ edge_weight(path[i], path[i+1]) for i in 0..|path|-2 ]
 2  confidences <- [ edge_conf(path[i], path[i+1])   for i in 0..|path|-2 ]
 3  avg_weight  <- mean(weights)
 4  path_conf   <- product(confidences)     # confidence compounds along a path
 5  depth_bonus <- 1 / sqrt(|path|)         # shorter paths preferred
 6  return avg_weight * path_conf * depth_bonus
```

### 4.12.3 Complexity

The replacement is O(*P*) in the number of simple paths within the cutoff, with
O(*top_n*) memory. The original was O(*V* · *P*): `all_simple_paths` was called
once per target vertex, and each call re-explored the entire reachable subgraph
to depth 4, yielding only the paths terminating at that target. It also
materialised a result dictionary, including a title lookup per node, for every
path before sorting and discarding all but ten.

Measured on layered synthetic graphs (Section 6.6.4), the redesign is 126× to
434× faster, with the gap widening as the graph grows, and returns an identical
top-ten verified against the exhaustive computation.

The `MAX_PATHS_EXAMINED` cap at line 13 is a safety valve rather than an
optimisation. A densely interlinked citation graph can contain an astronomical
number of simple paths; without a bound, one pathological input hangs the run.
When the cap triggers it is logged, so a truncated ranking is never presented
as exhaustive.
