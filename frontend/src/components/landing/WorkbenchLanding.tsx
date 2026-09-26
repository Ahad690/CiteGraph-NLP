/* Hallmark · genre: modern-minimal · macrostructure: Workbench · theme: Cobalt
 * enrichment: none (typography + one real product capture) · nav: N13 · footer: Ft2
 * pre-emit critique: P4 H4 E4 S5 R5 V4
 *
 * Every number on this page was read out of one real run of the deployed API --
 * seed 10.3389/fpubh.2024.1484210, run 751f7bca, 25 papers. Nothing is invented.
 * The previous landing page carried six fabricated testimonials with invented
 * institutions and three invented pricing tiers for a product with no accounts
 * and no billing; both sections are gone rather than reworded.
 *
 * The product capture is a Playwright screenshot of the live dashboard, not a
 * mock. It is the only image on the page.
 */
import { Link } from "@tanstack/react-router";
import graphCapture from "@/assets/workbench/citation-graph.png";

const RUN = {
  seed: "10.3389/fpubh.2024.1484210",
  runId: "751f7bca-1dd2-422c-bcb5-79eeb799220b",
  papers: 25,
  edges: 24,
  studies: 25,
  candidates: 34,
  resolutions: 25,
  paths: 10,
  warnings: [
    "Recovered 4 abstracts from Europe PMC that OpenAlex did not carry; population evidence needs abstract text.",
    "Recovered population evidence for 2 papers from Europe PMC open-access Methods/Results full text after the abstract was too thin.",
    "1 of 25 papers has no abstract in any provider; open-access full text was tried where available.",
  ],
};

const faqs = [
  {
    q: "What does it actually do with my identifier?",
    a: "It resolves the DOI, PMID, PMCID, title or URL against five catalogues, then walks the citation graph outward from that paper. The seed stays at the centre and each paper it reaches is a node you can open.",
  },
  {
    q: "Why is a population labelled ambiguous instead of guessed?",
    a: "Because a number scraped out of a sentence is often not the trial's sample. Where the extraction rules and the sentence disagree, the result is marked unscored rather than resolved to a plausible number. The disagreement rate is measured, not asserted.",
  },
  {
    q: "Where does the ranking come from?",
    a: "PageRank over the citation graph, plus a recency term and a study-size term. The seed is excluded from its own ranking. On this seed the ranking is empty, because a one-hop neighbourhood does not produce foundations -- the page shows that rather than hiding it.",
  },
  {
    q: "Is it free?",
    a: "The deployed instance is open and the source is yours to run. There is no account, no plan and no payment step, because there is no billing system behind this page to charge you for.",
  },
];

export function WorkbenchLanding() {
  return (
    <div className="theme-cobalt min-h-screen bg-paper text-ink-2">
      <Nav />
      <main>
        <Hero />
        <GraphTour />
        <GraphiteBand />
        <ConfidenceSection />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-rule bg-paper/90 backdrop-blur-[8px]">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-5">
        <Link to="/" className="font-display text-[15px] font-600 tracking-tight text-ink">
          CiteGraph-NLP
        </Link>
        <nav className="hidden items-center gap-5 sm:flex">
          <a href="#graph" className="link-signal text-[13px]">
            The graph
          </a>
          <a href="#confidence" className="link-signal text-[13px]">
            Confidence
          </a>
          <a href="#faq" className="link-signal text-[13px]">
            Questions
          </a>
        </nav>
        <div className="ml-auto flex items-center gap-2.5">
          <kbd className="hidden rounded border border-rule-2 px-1.5 py-0.5 font-mono text-[11px] text-ink-3 sm:block">
            ⌘K
          </kbd>
          <Link
            to="/start"
            className="rounded-md bg-signal px-3 py-1.5 text-[13px] font-500 text-signal-ink transition-colors hover:brightness-110"
          >
            Run a paper
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="border-b border-rule">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 py-20 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:py-28">
        {/* Left. Gate 6: never a centred hero. */}
        <div>
          <p className="label-mono flex items-center gap-2">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-signal" />
            Confidence-aware citation lineage
          </p>
          {/* The clamp tops out at 3.4rem, not 3.9rem: at 1440 the left column is
              about 600px, and 3.9rem wrapped "A defensible graph out." onto a third
              line, leaving "out." as an orphan. */}
          <h1 className="mt-5 text-[clamp(2.3rem,3.5vw+0.4rem,3.4rem)] leading-[1.05] tracking-[-0.03em] text-ink">
            One identifier in.
            <br />A defensible graph out.
          </h1>
          <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-ink-2">
            Paste a DOI and CiteGraph-NLP walks the citation graph outward, pulls the study
            population out of the text, and labels how sure it is. Where the evidence is thin it
            says so instead of rounding up.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
            <Link
              to="/start"
              className="rounded-md bg-signal px-4 py-2 text-[13px] font-500 text-signal-ink transition-colors hover:brightness-110"
            >
              Start a run
            </Link>
            <a href="#graph" className="link-signal text-[13px]">
              See a real run
            </a>
          </div>
        </div>

        {/* Right. Cobalt's signature move: code is the hero. A real request and a
            real response, with the run's actual counts. */}
        <div className="code-card overflow-hidden">
          <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5">
            <span className="font-mono text-[11px] tracking-[0.06em] text-graphite-ink-2">
              POST /api/runs
            </span>
            <span className="status--ok ml-auto">200 OK</span>
          </div>
          <pre className="overflow-x-auto px-4 py-3.5 text-[12.5px] leading-relaxed">
            <code>
              <span className="tok-punct">{`{`}</span>
              <span className="tok-key"> &quot;value&quot;</span>
              <span className="tok-punct">: </span>
              <span className="tok-str">&quot;{RUN.seed}&quot;</span>
              <span className="tok-punct">,</span>
              {"\n"}
              <span className="tok-key"> &quot;query_type&quot;</span>
              <span className="tok-punct">: </span>
              <span className="tok-str">&quot;doi&quot;</span>
              <span className="tok-punct">,</span>
              {"\n"}
              <span className="tok-key"> &quot;max_total_papers&quot;</span>
              <span className="tok-punct">: </span>
              <span className="tok-str">25</span>
              {"\n"}
              <span className="tok-punct">{`}`}</span>
            </code>
          </pre>
          <div className="border-t border-white/10 px-4 py-3.5 text-[12.5px] leading-relaxed">
            <pre className="overflow-x-auto">
              <code>
                <span className="tok-key">papers</span>
                <span className="tok-punct">: </span>
                <span className="tok-str">{RUN.papers}</span>
                <span className="tok-punct">,</span>
                <span className="tok-key">citation_edges</span>
                <span className="tok-punct">: </span>
                <span className="tok-str">{RUN.edges}</span>
                <span className="tok-punct">,</span>
                {"\n"}
                <span className="tok-key">population_resolutions</span>
                <span className="tok-punct">: </span>
                <span className="tok-str">{RUN.resolutions}</span>
                <span className="tok-punct">,</span>
                <span className="tok-key">ranked_paths</span>
                <span className="tok-punct">: </span>
                <span className="tok-str">{RUN.paths}</span>
                <span className="tok-punct">,</span>
                {"\n"}
                <span className="tok-key">ranked_foundational</span>
                <span className="tok-punct">: </span>
                <span className="tok-str">0</span>
                <span className="tok-punct">,</span>
                <span className="tok-key">warnings</span>
                <span className="tok-punct">: </span>
                <span className="tok-str">{RUN.warnings.length}</span>
              </code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}

function GraphTour() {
  return (
    <section id="graph" className="border-b border-rule">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <div className="max-w-2xl">
          <p className="label-mono">The graph</p>
          <h2 className="mt-4 text-[clamp(1.6rem,2.4vw+0.3rem,2.3rem)] leading-[1.1] tracking-[-0.025em] text-ink">
            The node colour is the confidence, not the topic.
          </h2>
          <p className="mt-4 text-[15px] leading-relaxed text-ink-2">
            This is the live dashboard, not an illustration. Node size is effective sample size;
            edge thickness is edge weight; the ring marks a foundational candidate. Grey means the
            population could not be resolved, and the legend says so.
          </p>
        </div>

        {/* Asymmetric, deliberately not three equal tiles (gate 3). */}
        <figure className="mt-10 overflow-hidden rounded-xl border border-rule bg-paper-raised">
          <img
            src={graphCapture}
            alt={`Citation graph from a real run: ${RUN.papers} papers and ${RUN.edges} citation edges, nodes coloured by resolved population confidence.`}
            width={1440}
            height={1000}
            loading="lazy"
            decoding="async"
            className="block w-full"
          />
          <figcaption className="border-t border-rule px-4 py-2.5 font-mono text-[11px] tracking-[0.06em] text-ink-3 uppercase">
            Run {RUN.runId.slice(0, 8)} · seed {RUN.seed} · {RUN.papers} papers
          </figcaption>
        </figure>

        <dl className="mt-10 grid gap-x-10 gap-y-7 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { k: "Papers resolved", v: RUN.papers, d: "one hop back from the seed" },
            { k: "Citation edges", v: RUN.edges, d: "each with a provider agreement weight" },
            { k: "Studies", v: RUN.studies, d: "papers collapsed onto registry identifiers" },
            {
              k: "Population candidates",
              v: RUN.candidates,
              d: `narrowed to ${RUN.resolutions} resolutions`,
            },
          ].map((item) => (
            <div key={item.k}>
              <dt className="label-mono">{item.k}</dt>
              <dd className="mt-2 font-display text-3xl font-600 tracking-tight text-ink">
                {item.v}
              </dd>
              <dd className="mt-1 text-[13px] text-ink-3">{item.d}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

/* Cobalt signature 8: one dark band per page, for a light -> dark -> light beat.
   This one carries the run's warnings verbatim, because a tool that only shows
   its successes is not telling you how far to trust it. */
function GraphiteBand() {
  return (
    <section className="band-graphite border-y border-rule">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.15fr]">
          <div>
            <p className="label-mono">What it could not get</p>
            <h2 className="mt-4 text-[clamp(1.5rem,2.2vw+0.3rem,2.1rem)] leading-[1.12] tracking-[-0.025em]">
              Three warnings came back with that run.
            </h2>
            <p className="mt-4 text-[14px] leading-relaxed text-graphite-ink-2">
              The API returns them instead of swallowing them. They are the reason the graph above
              is worth reading: you can see which parts of it are built on recovered text and which
              are not built at all.
            </p>
          </div>
          <ul className="space-y-4">
            {RUN.warnings.map((warning, index) => (
              <li key={index} className="flex gap-4 border-t border-white/10 pt-4">
                <span className="font-mono text-[11px] tracking-[0.06em] text-graphite-ink-2">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="text-[14px] leading-relaxed text-graphite-ink">{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function ConfidenceSection() {
  return (
    <section id="confidence" className="border-b border-rule">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-20 lg:grid-cols-2 lg:gap-16">
        <div>
          <p className="label-mono">Confidence</p>
          <h2 className="mt-4 text-[clamp(1.6rem,2.4vw+0.3rem,2.3rem)] leading-[1.1] tracking-[-0.025em] text-ink">
            A number you cannot trace is worse than no number.
          </h2>
        </div>
        <div className="space-y-6 text-[15px] leading-relaxed text-ink-2">
          <p>
            Population extraction reads sample sizes out of abstracts and, where a paper is open
            access, out of its Methods and Results. The rules that decide which sentence counts are
            explicit, and they were written down before the extractor was measured against them.
          </p>
          <p>
            Where a sentence is genuinely ambiguous — a cohort described but never sized, a flow
            that ends at an assessment rather than an analysis — the result is marked unscored
            instead of being resolved to the most plausible figure. That costs recall on purpose.
            The alternative is a graph that looks certain and is not.
          </p>
          <p className="text-ink-3">
            The blind second reading of the answer keys, and the disagreements that survived it, are
            written up in the project&rsquo;s thesis rather than summarised here.
          </p>
        </div>
      </div>
    </section>
  );
}

function Faq() {
  return (
    <section id="faq" className="border-b border-rule">
      <div className="mx-auto max-w-3xl px-5 py-20">
        <p className="label-mono">Questions</p>
        <h2 className="mt-4 text-[clamp(1.6rem,2.4vw+0.3rem,2.3rem)] leading-[1.1] tracking-[-0.025em] text-ink">
          The ones worth answering plainly.
        </h2>
        <dl className="mt-10">
          {faqs.map((item) => (
            <div key={item.q} className="border-t border-rule py-6">
              <dt className="font-display text-[16px] font-600 text-ink">{item.q}</dt>
              {/* ml-0: a dd keeps the browser's default 40px inline start, which
                  offset every answer from its own question. */}
              <dd className="mt-2.5 ml-0 text-[14.5px] leading-relaxed text-ink-2">{item.a}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section>
      <div className="mx-auto max-w-6xl px-5 py-20">
        <Link
          to="/start"
          className="inline-flex items-center gap-2 rounded-md bg-signal px-4 py-2 text-[13px] font-500 text-signal-ink transition-colors hover:brightness-110"
        >
          Start a run
          <span aria-hidden="true">&rarr;</span>
        </Link>
      </div>
    </section>
  );
}

/* Ft2: one inline line, a hairline above it. Not four columns of links. */
function Footer() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-5 py-7">
        <span className="font-display text-[13px] font-600 text-ink">CiteGraph-NLP</span>
        <span className="text-[13px] text-ink-3">
          Confidence-aware citation lineage for research graphs.
        </span>
        <span className="ml-auto font-mono text-[11px] tracking-[0.06em] text-ink-4 uppercase">
          Open source · MIT
        </span>
      </div>
    </footer>
  );
}
