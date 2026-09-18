# Chapter 2: Literature Review

This chapter surveys four bodies of work that the project draws on: citation
analysis and bibliometrics (2.1), the structure of citation networks (2.2),
scholarly data infrastructure (2.3), and biomedical information extraction
(2.4). Section 2.5 reviews evidence appraisal, which supplies the project's
motivating assumption. Section 2.6 states the gap.

Every work cited in this chapter was resolved against Crossref or OpenAlex
before being cited; the verification procedure and the resulting metadata are
given in Appendix E. Three candidate references were discarded during that
process because the identifiers initially assigned to them resolved to
different papers; this is reported in Section 6.7 as a methodological note.

## 2.1 Citation Indexing and Bibliometric Indicators

### 2.1.1 The citation index

Garfield's 1955 proposal introduced the citation index as an instrument for
science rather than merely a bibliographic convenience [garfield1955]. The
central argument was that the citation is a *directed assertion of dependence*,
and that a machine-readable index of such assertions would let a reader move
through the literature along lines of intellectual descent rather than by
subject heading. The paper anticipates the use this project makes of citation
data: following edges backwards to reach antecedents.

Garfield also anticipated the failure mode. He noted that a citation may be
critical as easily as supportive, and that an index records the link without
recording its valence. This limitation is unresolved seventy years on and
applies directly to the present work: CiteGraph-NLP treats every citation as a
positive dependency because the available APIs expose no sentiment.

### 2.1.2 Count-based indicators and their known confounds

The h-index [hirsch2005hindex] proposed a single number combining productivity
and impact: an author has index *h* if *h* of their papers have at least *h*
citations each. Its appeal is robustness to both a long tail of uncited work
and a single exceptional paper.

Waltman's review of citation impact indicators [waltman2016review] surveys the
subsequent literature and catalogues the confounds that affect this whole
family of measures. Three matter here. Citation practice differs by field, so
raw counts are not comparable across disciplines. Counts accumulate with time,
so older papers are advantaged and recent work is systematically
under-represented. And review articles attract citations disproportionately to
primary studies, which is precisely inverted relative to what a reader tracing
foundational evidence wants.

This project responds to the third confound directly. The foundational ranking
described in Section 4.6 combines PageRank with an age term, deliberately
advantaging older work, because the target is the origin of a line of research
rather than its most popular recent summary. Whether this succeeds is examined
in Section 6.5, and Section 7.3 notes that no formal relevance study was run.

## 2.2 Structure and Dynamics of Citation Networks

### 2.2.1 Empirical distribution of citations

Redner's empirical study of citation distributions [redner1998citation]
established that citation counts are extremely heavy-tailed: the large majority
of papers receive few citations while a small minority receive very many.
Radicchi and colleagues [radicchi2008universality] showed that after
normalising by field-average citation count, the distributions across
disciplines collapse onto a common curve, which both explains the
incomparability of raw counts and suggests a normalisation.

The practical consequence for this project is a design constraint rather than a
theoretical one. Because the distribution is heavy-tailed, a seed paper may
have tens of thousands of citing works, the AlphaFold paper used as a test case
in Chapter 6 has over thirty thousand. No interactive traversal can enumerate
them. Section 4.5 describes the sampling strategy this forces, and Section 7.3
treats the resulting incompleteness as a threat to validity.

### 2.2.2 Network models of scientific collaboration and citation

Newman's analysis of scientific collaboration networks [newman2001structure]
characterised the small-world and clustering properties of coauthorship graphs.
Although coauthorship is not citation, the structural findings, short path
lengths, high clustering, heavy-tailed degree, recur in citation graphs and
bear on this system: short paths mean a bounded-depth traversal reaches
substantial portions of a local neighbourhood, and high clustering means the
papers retrieved tend to be topically coherent, which is observed empirically
in Section 6.5.

### 2.2.3 PageRank applied to citation networks

Brin and Page's description of the Google search engine [brin1998anatomy]
introduced PageRank as a recursive measure of importance over a directed graph:
a node is important if important nodes point to it. The method was devised for
hyperlinks, but citation graphs are directed graphs of the same shape.

Chen and colleagues applied PageRank directly to a physics citation network
[chen2007gems] and found that it surfaces papers that raw citation count does
not, work that is cited by influential papers rather than by many papers. They
characterise these as "scientific gems". Walker and colleagues proposed
CiteRank [walker2007citerank], a model of network traffic that adds an explicit
ageing term so that recent papers are not penalised purely for having had less
time to accumulate citations.

These two papers are the closest prior art to the ranking component of this
project, and the relationship should be stated plainly: **the ranking method
used here is not novel.** PageRank over a citation graph, with an age
adjustment, is exactly what Chen et al. and Walker et al. describe. The
difference in this work is not the algorithm but the *edge weights* it operates
on. Chen et al. run PageRank over an unweighted citation graph; CiteRank
weights by age. CiteGraph-NLP weights each edge by extracted study-scale
evidence. Whether that weighting is an improvement is not established by this
thesis and is not claimed; Section 7.3 is explicit that no comparative ranking
experiment against an unweighted baseline was conducted.

### 2.2.4 Co-citation analysis and visualisation

Chen's CiteSpace [chen2007cocitation] provides interactive visual analytics over
co-citation networks, detecting emerging trends and intellectual turning points.
It shares this project's premise that a citation network is best interrogated
visually and interactively rather than reduced to a ranking. It differs in
unit of analysis: CiteSpace works from a corpus supplied by the user, typically
a search result set, whereas CiteGraph-NLP expands outward from a single seed.

## 2.3 Scholarly Data Infrastructure

The feasibility of this project rests entirely on the availability of open
citation data. Four sources are relevant.

**Crossref** [hendricks2020crossref] is the DOI registration agency for
scholarly publishing and the canonical source for publisher-deposited metadata,
including reference lists where publishers deposit them. Crossref's coverage of
reference lists is uneven because deposit is at publisher discretion, a
limitation this project encountered directly and quantified in Section 6.3.

**OpenAlex** [priem2022openalex] is an open catalogue of scholarly works
succeeding the discontinued Microsoft Academic Graph. It provides works,
authors, venues and, critically here, both `referenced_works` and a `cites`
filter supporting forward citation queries. It is the primary provider in this
system.

**Microsoft Academic Graph** [wang2020mag] was the prior generation of this
infrastructure. Its discontinuation, and OpenAlex's emergence as successor, is
a reminder that a system built on a single provider inherits that provider's
lifespan, one motivation for the multi-provider design in Section 4.3.

**Europe PMC** [europepmc2015] is a full-text literature database for the life
sciences providing abstracts and, for open-access content, full text. In this
system it began as a third metadata provider and became, as measured in
Section 6.3, the decisive source of abstract text: 28% of papers in a
representative graph carried no abstract in OpenAlex, and all of them were
recoverable from Europe PMC.

**Unpaywall** [martin2021oadoi] characterises the open-access state of the
literature. Its relevance is to the full-text extension discussed in
Section 8.2: any move from abstracts to full text must first determine which
articles are legally retrievable.

## 2.4 Biomedical Information Extraction

### 2.4.1 Annotated corpora

The GENIA corpus [kim2003genia] established the pattern for biomedical IE
evaluation: a semantically annotated corpus of abstracts supporting supervised
training and comparable evaluation. Its significance for this project is
methodological, it demonstrates that abstract-level annotation is a legitimate
evaluation substrate, which is the basis for the gold standard in Section 6.1.

### 2.4.2 PICO extraction

The task closest to this project's extraction component is PICO element
detection: identifying Population, Intervention, Comparison and Outcome spans in
clinical abstracts. The EBM-NLP corpus [nye2018ebmnlp] provides multi-level
annotations of these elements over a large set of abstracts. Jin and Szolovits
[jin2018pico] approach the detection task with LSTM models.

The *P* of PICO is the element this project extracts, but with an important
narrowing. PICO population annotation captures the described population,
"adults over 65 with type 2 diabetes", as a text span. CiteGraph-NLP extracts
the *cardinality* of that population: the integer count of subjects. These are
related but distinct tasks, and the distinction matters when comparing results.
A PICO system that correctly identifies a population span has not necessarily
identified a sample size.

The methodological gap is worth stating plainly: EBM-NLP and the systems trained
on it are supervised, trained on thousands of annotated abstracts. This project
uses hand-written patterns evaluated on twenty. Section 7.3 treats the resulting
limits on generalisability as the principal threat to validity in the extraction
results, and Section 8.2 identifies supervised extraction as the clearest
improvement path.

### 2.4.3 Domain-adapted language models

BioBERT [lee2020biobert] and SciBERT [beltagy2019scibert] demonstrated that
pretraining transformer models on biomedical and scientific text respectively
yields substantial gains over general-domain models on domain tasks. ScispaCy
[neumann2019scispacy] packages practical biomedical NLP pipelines.

None of these is used in the delivered system, which extracts using regular
expressions. This is a deliberate scope decision rather than an oversight, and
the trade-off should be stated honestly. Pattern-based extraction is
transparent, every decision traces to a named pattern and can be explained to a
user, and requires no training data, which the project did not have. It is also
brittle in exactly the way Section 6.4 measures: the system distinguishes
*randomised* from *enrolled* from *analysed* correctly in only 6 of 10 cases, a
discrimination a domain-adapted model would be expected to make more reliably.

### 2.4.4 Automated evidence appraisal

RobotReviewer [marshall2016robotreviewer] automatically assesses risk of bias in
clinical trial reports, and Trialstreamer [marshall2020trialstreamer] maintains a
living, automatically updated database of randomised controlled trials with
extracted characteristics including sample size.

Trialstreamer is the nearest system-level prior art to this project, and the
comparison is instructive rather than favourable. Trialstreamer extracts trial
characteristics at scale using trained models over full text, with published
evaluation. CiteGraph-NLP extracts one characteristic from abstracts using
patterns, evaluated on twenty papers. What this project does that Trialstreamer
does not is use the extracted scale *as a citation-graph edge weight*, the
combination of extraction with network analysis is where the work sits, not in
the extraction itself.

## 2.5 Evidence Appraisal and the Role of Study Size

The premise that sample size is a meaningful proxy for evidential weight is
supported by, but not identical to, the methodological literature.

PRISMA [moher2009prisma] standardises the reporting of systematic reviews, and
the Cochrane risk-of-bias tool [higgins2011cochrane] structures appraisal of
individual trials. Both make clear that sample size is *one* dimension among
several, allocation concealment, blinding, attrition and selective reporting
all bear on trustworthiness, and none is captured by a participant count.

Ioannidis [ioannidis2005why] and Button et al. [button2013power] supply the
argument for why size nonetheless matters: underpowered studies both miss true
effects and inflate the proportion of detected effects that are spurious.

The honest position for this project is therefore narrow. Sample size is a
*cheaply extractable* signal that correlates with evidential weight and is
currently absent from citation graphs. It is not a measure of study quality,
and the system must not be presented as appraising quality. Section 4.7
describes how this caution is surfaced in the interface, and the generated
analysis reports carry an explicit statement to that effect.

## 2.6 Synthesis and Research Gap

The reviewed literature supports four observations.

1. Citation graphs are navigable and machine-readable at scale
   [garfield1955; priem2022openalex; hendricks2020crossref].
2. Count-based indicators are confounded, and PageRank-family methods over
   citation graphs partially address this [waltman2016review; chen2007gems;
   walker2007citerank].
3. Study characteristics including sample size can be extracted automatically
   from clinical text [nye2018ebmnlp; marshall2020trialstreamer].
4. Sample size is one legitimate, if partial, component of evidential weight
   [ioannidis2005why; button2013power].

Observations 2 and 3 have developed largely independently. Citation-graph
analysis treats edges as uniform; evidence extraction produces study
characteristics that are used for search and synthesis but not fed back into the
network. **The gap this project addresses is the connection between them: using
automatically extracted study-scale evidence as a weight on citation edges, and
propagating that weight through a graph ranking.**

Two qualifications bound the claim. First, the components are individually
established; the contribution is their combination and a measured account of
how well it works, not a new method. Second, this thesis does not demonstrate
that evidence-weighted ranking is *better* than unweighted ranking, no
comparative experiment was performed, and Section 7.3 states this as the
principal unaddressed question.

---
