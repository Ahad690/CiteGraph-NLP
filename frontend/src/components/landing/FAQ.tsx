import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { SectionHeader } from "./SectionHeader";
import { trackEvent } from "@/lib/analytics";

const faqs = [
  { badge: "Research Accuracy", q: "Does CiteGraph-NLP find the original paper behind a research idea?", a: "No tool can guarantee the absolute original paper because citation databases are incomplete and research ideas evolve gradually. CiteGraph-NLP identifies probable foundational papers using citation position, graph connectivity, study-scale evidence, and confidence-aware ranking." },
  { badge: "Input", q: "What input types are supported?", a: "The system is designed to support DOI, PMID, PMCID, paper title, and uploaded PDF. The recommended workflow is identifier-first, meaning the system tries to resolve metadata through APIs before parsing full text." },
  { badge: "Metadata", q: "Which metadata sources does it use?", a: "CiteGraph-NLP is designed to work with public scholarly metadata sources such as OpenAlex, Crossref, Europe PMC, PubMed, and Semantic Scholar. Availability depends on the provider and paper." },
  { badge: "NLP", q: "How does population-size extraction work?", a: "The system uses NLP and rule-based extraction to detect candidate population values such as randomized patients, enrolled participants, analyzed cohorts, and arm sizes. Each value is classified and assigned a confidence score." },
  { badge: "Confidence", q: "Can it perfectly extract sample sizes?", a: "No. Research papers often contain many numbers, and not every number is a study population. CiteGraph-NLP makes uncertainty visible by labeling ambiguous or missing extractions instead of pretending every value is correct." },
  { badge: "Population", q: "What is N_eff?", a: "N_eff is the system's selected effective population size for a paper or study. It may represent randomized, analyzed, enrolled, or inferred population size depending on the evidence and confidence score." },
  { badge: "Graph", q: "What is a confidence-aware citation weight?", a: "Citation edge weights combine normalized population-size evidence, journal/source metrics, and extraction confidence. Low-confidence population evidence reduces the final weight." },
  { badge: "Scope", q: "Is this only for biomedical research?", a: "The prototype works best for biomedical and clinical papers because they often contain structured metadata and population-size evidence. The graph and metadata parts can still apply to other domains." },
  { badge: "Export", q: "Can I export the results?", a: "Yes. The planned exports include JSON reports, CSV tables, GraphML for graph tools, and Markdown reports for documentation or submission." },
  { badge: "Students", q: "Is this suitable for an NLP course project?", a: "Yes. It combines metadata resolution, PDF parsing, NLP extraction, citation traversal, graph construction, confidence scoring, and visualization into one realistic project." },
];

export function FAQ() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="relative py-24 bg-gradient-to-b from-transparent via-slate-950/40 to-transparent">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="FAQ"
          title={<>Frequently asked <span className="text-gradient-brand">questions</span></>}
          subtitle="Everything you need to know about confidence-aware citation lineage analysis."
        />
        <div className="mt-12 space-y-3">
          {faqs.map((f, i) => {
            const isOpen = open === i;
            return (
              <div key={f.q} className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl overflow-hidden">
                <button
                  onClick={() => {
                    setOpen(isOpen ? null : i);
                    if (!isOpen) trackEvent("faq_item_expand", { q: f.q });
                  }}
                  className="w-full px-5 py-4 flex items-center justify-between gap-4 text-left hover:bg-slate-800/40 transition"
                  aria-expanded={isOpen}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] uppercase tracking-[0.14em] text-cyan-200 bg-cyan-400/10 border border-cyan-400/20 rounded-full px-2 py-0.5 hidden sm:inline">{f.badge}</span>
                    <span className="font-medium text-white">{f.q}</span>
                  </div>
                  <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                </button>
                {isOpen && (
                  <div className="px-5 pb-5 text-sm text-slate-300 leading-relaxed animate-fade-in">{f.a}</div>
                )}
              </div>
            );
          })}
        </div>
        <p className="mt-10 text-center text-sm text-slate-400">
          Still have questions? <a className="text-cyan-300 hover:underline" href="mailto:research@citegraph-nlp.app">Contact us at research@citegraph-nlp.app →</a>
        </p>
      </div>
    </section>
  );
}
