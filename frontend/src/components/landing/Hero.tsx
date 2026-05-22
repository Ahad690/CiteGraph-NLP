import { Link } from "@tanstack/react-router";
import { Search, PlayCircle, Check } from "lucide-react";
import { trackEvent } from "@/lib/analytics";
import { Backdrop } from "./Backdrop";

export function Hero() {
  return (
    <section className="relative pt-32 md:pt-40 pb-16 md:pb-24 overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(79,70,229,0.25),transparent_35%),radial-gradient(circle_at_top_right,rgba(6,182,212,0.18),transparent_32%),linear-gradient(135deg,#020617,#0f172a,#111827)]">
      <Backdrop />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-1.5 text-sm font-medium text-cyan-200 animate-fade-in">
          <span aria-hidden>🧠</span> NLP-powered citation lineage analysis
        </div>

        <h1 className="mt-6 text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05] text-white animate-slide-up">
          Trace research ideas through citation graphs.
          <br />
          <span className="text-gradient-brand">Find probable foundational papers.</span>
        </h1>

        <p className="mt-6 text-lg md:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed animate-slide-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
          CiteGraph-NLP turns a DOI, PMID, paper title, or PDF into a confidence-aware
          research knowledge graph — revealing citation lineage, study population evidence,
          and evidence-weighted foundational papers.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-300">
          {["Confidence-aware extraction", "Citation lineage mapping", "Study-scale evidence ranking"].map((b) => (
            <span key={b} className="inline-flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald" /> {b}
            </span>
          ))}
        </div>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/start"
            onClick={() => trackEvent("hero_cta_click")}
            className="group inline-flex items-center gap-2 bg-gradient-to-r from-indigo to-cyan text-white px-7 py-3.5 rounded-xl font-semibold shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all hover:-translate-y-0.5"
          >
            <Search className="w-5 h-5" /> Start Analysis
          </Link>
          <a
            href="#showcase"
            onClick={() => trackEvent("hero_demo_click")}
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-slate-100 border border-slate-700 hover:border-cyan-400/40 hover:bg-slate-900/60 transition"
          >
            <PlayCircle className="w-5 h-5" /> View Demo Graph
          </a>
        </div>

        <p className="mt-10 text-sm text-slate-400">
          Built for researchers, NLP students, and evidence-driven literature review.
        </p>
        <div className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">
          Designed to work with metadata sources such as
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-400">
          {["OpenAlex", "Crossref", "PubMed", "Europe PMC", "Semantic Scholar"].map((s) => (
            <span key={s} className="opacity-80">{s}</span>
          ))}
        </div>
      </div>
    </section>
  );
}
