import { Link } from "@tanstack/react-router";
import { Network, Search, PlayCircle, Check } from "lucide-react";
import { trackEvent } from "@/lib/analytics";

export function FinalCTA() {
  return (
    <section className="relative py-24 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(79,70,229,0.25),transparent_55%),radial-gradient(circle_at_70%_30%,rgba(6,182,212,0.18),transparent_45%)]" />
      <div className="relative mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl border border-cyan-400/20 bg-slate-950/70 backdrop-blur-xl p-10 md:p-14 text-center shadow-2xl shadow-cyan-500/10">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo to-cyan grid place-items-center shadow-lg shadow-cyan-500/30">
            <Network className="w-7 h-7 text-white" />
          </div>
          <h2 className="mt-6 text-3xl md:text-5xl font-bold tracking-tight text-white leading-tight">
            Ready to map the lineage behind your next paper?
          </h2>
          <p className="mt-4 text-lg text-gradient-brand font-semibold">
            Go from one DOI to an evidence-weighted citation graph.
          </p>
          <p className="mt-4 text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Start with a paper identifier and explore probable foundational studies, population evidence, and confidence-aware rankings in minutes.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-300">
            {["No overclaiming", "Confidence-aware", "Exportable reports"].map((b) => (
              <span key={b} className="inline-flex items-center gap-2"><Check className="w-4 h-4 text-emerald" /> {b}</span>
            ))}
          </div>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/start"
              onClick={() => trackEvent("final_cta_click", { which: "primary" })}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo to-cyan text-white px-7 py-3.5 rounded-xl font-semibold shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 transition"
            >
              <Search className="w-5 h-5" /> Start Analysis
            </Link>
            <Link
              to="/dashboard/$runId"
              params={{ runId: "demo_run_001" }}
              onClick={() => trackEvent("final_cta_click", { which: "secondary" })}
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-slate-100 border border-slate-700 hover:border-cyan-400/40 hover:bg-slate-900/60 transition"
            >
              <PlayCircle className="w-5 h-5" /> View Demo Graph
            </Link>
          </div>
          <p className="mt-8 text-sm text-slate-400">Built for NLP students, researchers, and evidence-driven literature review.</p>
        </div>
      </div>
    </section>
  );
}
